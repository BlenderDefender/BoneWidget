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
    Collection,
    Context,
    LayerCollection,
    Object,
    PoseBone
)

from mathutils import Matrix

import typing

from .. import (
    __package__,
    custom_types
)

def get_widget_prefix(context: 'Context') -> str:
    """Get the widget prefix.

    Args:
        context (Context): The current Blender context

    Returns:
        str: The widget prefix
    """
    prefs: 'custom_types.AddonPreferences' = context.preferences.addons[__package__.split(".")[0]].preferences

    prefix = prefs.widget_prefix

    if context.active_object:
        prefix = prefix.replace("{object}", context.active_object.name)

    return prefix


def get_collection_name(context: 'Context') -> str:
    """Get the name of the widget collection.

    Args:
        context (Context): The current Blender context

    Returns:
        str: The name of the widget collection
    """

    prefs: 'custom_types.AddonPreferences' = context.preferences.addons[__package__.split(".")[0]].preferences

    collection_name = prefs.bonewidget_collection_name

    if context.active_object:
        collection_name = collection_name.replace("{object}", context.active_object.name)

    return collection_name


def get_collection(context: 'Context') -> 'Collection':
    """Get the collection, where the widget objects are stored.

    Args:
        context (Context): The current Blender context.

    Returns:
        Collection: The collection to store widget objects in.
    """

    bw_collection_name: str = get_collection_name(context)
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

    widget_collection: 'Collection' = bpy.data.objects[widget.name].users_collection[0]
    active_layer_collection: 'LayerCollection' = context.view_layer.layer_collection

    # Find the widget collection in the current view layer
    layer_collection: 'LayerCollection' = recursively_find_layer_collection(
        active_layer_collection, widget_collection.name)

    # Make sure the widget collection is not hidden on a data level
    widget_collection.hide_viewport = False

    context.view_layer.active_layer_collection = layer_collection

    # Make sure the widget collection isn't excluded in the view layer, so it can be edited
    layer_collection.exclude = False

    context.view_layer.active_layer_collection = active_layer_collection

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
