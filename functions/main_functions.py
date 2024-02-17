# ##### BEGIN GPL LICENSE BLOCK #####
#
# Copyright (C) 2020 Manuel Rais
# manu@g-lul.com

# Created by Manuel Rais and Christophe Seux

#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.

import bpy
from bpy.types import (
    Armature,
    Collection,
    Context,
    LayerCollection,
    Object,
    PoseBone
)

import numpy
from mathutils import Matrix

import typing

from .. import (
    __package__,
    custom_types
)


def get_collection(context: 'Context') -> 'Collection':
    """Get the collection, where the widget objects are stored.

    Args:
        context (Context): The current Blender context.

    Returns:
        Collection: The collection to store widget objects in.
    """

    prefs: 'custom_types.AddonPreferences' = context.preferences.addons[__package__].preferences

    bw_collection_name: str = prefs.bonewidget_collection_name
    # collection = context.scene.collection.children.get(bw_collection_name)
    collection: 'Collection' = recursively_find_layer_collection(
        context.scene.collection, bw_collection_name)
    if collection:  # if it already exists
        return collection

    collection = bpy.data.collections.get(bw_collection_name)

    if collection:  # if it exists but not linked to scene
        context.scene.collection.children.link(collection)
        return collection

    # create a new collection
    collection = bpy.data.collections.new(bw_collection_name)
    context.scene.collection.children.link(collection)
    # hide new collection
    viewlayer_collection = context.view_layer.layer_collection.children[collection.name]
    viewlayer_collection.hide_viewport = True
    return collection


def recursively_find_layer_collection(layer_collection: 'Collection', collection_name: str) -> 'Collection':
    """Recursively find a collection with a specified collection name.

    Args:
        layer_collection (Collection): The collection to start searching from.
        collection_name (str): The name of the searched collection.

    Returns:
        Collection: The collection that has been searched for.
    """

    found: 'Collection' = None

    if layer_collection.name == collection_name:
        return layer_collection

    for layer in layer_collection.children:
        found = recursively_find_layer_collection(layer, collection_name)
        if found:
            return found


def get_view_layer_collection(context: 'Context', widget: 'Object' = None) -> 'LayerCollection':
    """Get the view layer collection of the widget object.

    Args:
        context (Context): The current Blender context.
        widget (Object, optional): The widget of which the view layer collection should be searched. Defaults to None.

    Returns:
        LayerCollection: The view layer collection of the widget object.
    """

    widget_collection: 'Collection' = bpy.data.collections[
        bpy.data.objects[widget.name].users_collection[0].name]
    # save current active layer_collection
    saved_layer_collection: 'LayerCollection' = context.view_layer.layer_collection
    # actually find the view_layer we want
    layer_collection: 'LayerCollection' = recursively_find_layer_collection(
        saved_layer_collection, widget_collection.name)
    # make sure the collection (data level) is not hidden
    widget_collection.hide_viewport = False

    # change the active view layer
    context.view_layer.active_layer_collection = layer_collection
    # make sure it isn't excluded so it can be edited
    layer_collection.exclude = False
    # return the active view layer to what it was
    context.view_layer.active_layer_collection = saved_layer_collection

    return layer_collection


def bone_matrix(context: 'Context', widget: 'Object', match_bone: 'PoseBone'):
    """Update the transforms of the widget object to match the transforms of the bone.

    Args:
        context (Context): The current Blender context.
        widget (Object): The widget object.
        match_bone (PoseBone): The bone to match the transforms of.
    """

    if widget == None:
        return

    widget.matrix_local = match_bone.bone.matrix_local

    # Multiply the bones world matrix with the bones local matrix.
    widget.matrix_world = match_bone.id_data.matrix_world @ match_bone.bone.matrix_local
    if match_bone.custom_shape_transform:
        # if it has a tranform override apply this to the widget loc and rot
        org_scale = widget.matrix_world.to_scale()
        org_scale_mat = Matrix.Scale(1, 4, org_scale)
        target_matrix = match_bone.custom_shape_transform.id_data.matrix_world @ match_bone.custom_shape_transform.bone.matrix_local
        loc = target_matrix.to_translation()
        loc_mat = Matrix.Translation(loc)
        rot = target_matrix.to_euler().to_matrix()
        widget.matrix_world = loc_mat @ rot.to_4x4() @ org_scale_mat

    if match_bone.use_custom_shape_bone_size:
        ob_scale = context.scene.objects[match_bone.id_data.name].scale
        widget.scale = [match_bone.bone.length * ob_scale[0],
                        match_bone.bone.length * ob_scale[1], match_bone.bone.length * ob_scale[2]]
        # widget.scale = [match_bone.bone.length, match_bone.bone.length, match_bone.bone.length]
    widget.data.update()


def from_widget_find_bone(widget: 'Object') -> 'PoseBone':
    """Given an object, try to find the Bone that the object is a custom widget of.

    Args:
        widget (Object): The (widget) object.

    Returns:
        PoseBone: The bone, that the object is a widget of.
    """

    context = bpy.context

    match_bone = None
    for ob in context.scene.objects:
        ob: 'Object'
        if ob.type != "ARMATURE":
            continue

        for bone in ob.pose.bones:
            bone: 'PoseBone'
            if bone.custom_shape == widget:
                match_bone: 'PoseBone' = bone
    return match_bone


def symmetrize_widget(bone: 'PoseBone', collection: 'LayerCollection'):
    """Symmetrize a widget to the opposite site (e.g. from Bone.L to Bone.R).
    Works only, if the objects have the symmetry suffix.

    Args:
        bone (PoseBone): The bone with the custom widget.
        collection (LayerCollection): The collection to create widgets in.
    """

    context = bpy.context
    D = bpy.data

    prefs: 'custom_types.AddonPreferences' = context.preferences.addons[__package__].preferences

    bw_widget_prefix: str = prefs.widget_prefix

    widget = bone.custom_shape

    mirror_object = find_mirror_object(bone)
    if not mirror_object:
        return

    mirror_bone: 'PoseBone' = mirror_object
    if mirror_object.custom_shape_transform:
        mirror_bone: 'PoseBone' = mirror_object.custom_shape_transform

    mirror_widget: 'Object' = mirror_bone.custom_shape
    if mirror_widget != widget:
        mirror_widget.name = mirror_widget.name + "_old"
        mirror_widget.data.name = mirror_widget.data.name + "_old"
        # unlink/delete old widget
        if context.scene.objects.get(mirror_widget.name):
            D.objects.remove(mirror_widget)

    new_data = widget.data.copy()
    for vert in new_data.vertices:
        vert.co = numpy.array(vert.co) * (-1, 1, 1)

    new_object: 'Object' = widget.copy()
    new_object.data = new_data
    new_data.update()
    new_object.name = bw_widget_prefix + mirror_bone.name
    D.collections[collection.name].objects.link(new_object)
    new_object.matrix_local = mirror_bone.bone.matrix_local
    new_object.scale = [mirror_bone.bone.length,
                        mirror_bone.bone.length, mirror_bone.bone.length]

    layer = context.view_layer
    layer.update()

    mirror_bone.custom_shape = new_object
    mirror_bone.bone.show_wire = True


def symmetrize_widget_helper(bone: 'PoseBone', collection: 'LayerCollection', active_object: 'PoseBone', widgets_and_bones: dict):
    """Wrapper function for symmetrize_widget, that takes care of checking,
    if the conditions for symmetrizing widgets are met.

    Args:
        bone (PoseBone): A bone from widgets_and_bones. TODO: This is unnecessary, see double if-check.
        collection (LayerCollection): The current view layer collection
        active_object (PoseBone): The currently active bone
        widgets_and_bones (dict): A dictionary of bones and their custom shapes, if they have a symmetry suffix.
    """

    context = bpy.context

    prefs: 'custom_types.AddonPreferences' = context.preferences.addons[__package__].preferences

    bw_symmetry_suffix: str = prefs.symmetry_suffix
    bw_symmetry_suffix = bw_symmetry_suffix.split(";")

    suffix_1 = bw_symmetry_suffix[0].replace(" ", "")
    suffix_2 = bw_symmetry_suffix[1].replace(" ", "")

    if active_object.name.endswith(suffix_1):
        if bone.name.endswith(suffix_1) and widgets_and_bones[bone]:
            symmetrize_widget(bone, collection)
    elif active_object.name.endswith(suffix_2):
        if bone.name.endswith(suffix_2) and widgets_and_bones[bone]:
            symmetrize_widget(bone, collection)


def find_mirror_object(object: 'Object') -> typing.Union['Object', 'PoseBone']:
    """Find the object that, according to the name and suffix, can be used for mirroring widgets.

    Args:
        object (Object): The object that should be mirrored from.

    Returns:
        typing.Union['Object', 'PoseBone']: The object that can be used for mirroring widgets.
    """

    context = bpy.context
    D = bpy.data

    prefs: 'custom_types.AddonPreferences' = context.preferences.addons[__package__].preferences

    bw_symmetry_suffix = prefs.symmetry_suffix
    bw_symmetry_suffix: str = bw_symmetry_suffix.split(";")

    suffix_1 = bw_symmetry_suffix[0].replace(" ", "")
    suffix_2 = bw_symmetry_suffix[1].replace(" ", "")

    if object.name.endswith(suffix_1):
        suffix = suffix_2
        suffix_length = len(suffix_1)

    elif object.name.endswith(suffix_2):
        suffix = suffix_1
        suffix_length = len(suffix_2)

    elif object.name.endswith(suffix_1.lower()):
        suffix = suffix_2.lower()
        suffix_length = len(suffix_1)
    elif object.name.endswith(suffix_2.lower()):
        suffix = suffix_1.lower()
        suffix_length = len(suffix_2)
    else:  # what if the widget ends in .001?
        print('Object suffix unknown, using blank')
        suffix = ''

    object_name = list(object.name)
    object_base_name = object_name[:-suffix_length]
    mirrored_object_name = "".join(object_base_name) + suffix

    if object.id_data.type == 'ARMATURE':
        return object.id_data.pose.bones.get(mirrored_object_name)
    else:
        return context.scene.objects.get(mirrored_object_name)


def find_match_bones() -> tuple:
    """Find all pairs of matching bones as dictionary.

    Returns:
        tuple: (widgets_and_bones, active_object, armature)
            `widgets_and_bones` is a dictionary of bones and their custom shapes, if they have a symmetry suffix.
            `active_object` is the active pose bone.
            `armature` is the active armature.
    """

    context = bpy.context
    D = bpy.data

    prefs: 'custom_types.AddonPreferences' = context.preferences.addons[__package__].preferences

    bw_symmetry_suffix: str = prefs.symmetry_suffix
    bw_symmetry_suffix = bw_symmetry_suffix.split(";")

    suffix_1 = bw_symmetry_suffix[0].replace(" ", "")
    suffix_2 = bw_symmetry_suffix[1].replace(" ", "")

    widgets_and_bones: dict = {}

    if context.object.type == 'ARMATURE':
        for bone in context.selected_pose_bones:
            if bone.name.endswith(suffix_1) or bone.name.endswith(suffix_2):
                widgets_and_bones[bone] = bone.custom_shape
                mirror_bone = find_mirror_object(bone)
                if mirror_bone:
                    widgets_and_bones[mirror_bone] = mirror_bone.custom_shape

        armature = context.object
        active_object = context.active_pose_bone
        return (widgets_and_bones, active_object, armature)

    # Never reached, due to poll.
    for shape in context.selected_objects:
        bone = from_widget_find_bone(shape)
        if bone.name.endswith(("L", "R")):
            widgets_and_bones[from_widget_find_bone(shape)] = shape

            mirror_shape = find_mirror_object(shape)
            if mirror_shape:
                widgets_and_bones[mirror_shape] = mirror_shape

    active_object = from_widget_find_bone(context.object)
    armature = active_object.id_data

    return (widgets_and_bones, active_object, armature)
