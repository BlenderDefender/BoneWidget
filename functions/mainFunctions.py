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
import numpy
from math import pi
from mathutils import Matrix
from .jsonFunctions import objectDataToDico
from .. import __package__


def getCollection(context):
    bw_collection_name = context.preferences.addons[__package__].preferences.bonewidget_collection_name
    #collection = context.scene.collection.children.get(bw_collection_name)
    collection = recurLayerCollection(
        context.scene.collection, bw_collection_name)
    if collection:  # if it already exists
        return collection

    collection = bpy.data.collections.get(bw_collection_name)

    if collection:  # if it exists but not linked to scene
        context.scene.collection.children.link(collection)
        return collection

    else:  # create a new collection
        collection = bpy.data.collections.new(bw_collection_name)
        context.scene.collection.children.link(collection)
        # hide new collection
        viewlayer_collection = context.view_layer.layer_collection.children[collection.name]
        viewlayer_collection.hide_viewport = True
        return collection

# ! Old code
# def getViewLayerCollection(context, widget=None):
#     bw_collection_name = context.preferences.addons[__package__].preferences.bonewidget_collection_name
#     collection = context.view_layer.layer_collection.children[bw_collection_name]
#     try:
#         collection = context.view_layer.layer_collection.children[bw_collection_name]
#     except KeyError:
#         # need to find the collection it is actually in
#         collection = context.view_layer.layer_collection.children[
#             bpy.data.objects[widget.name].users_collection[0].name]


def recurLayerCollection(layer_collection, collection_name):
    found = None
    if (layer_collection.name == collection_name):
        return layer_collection
    for layer in layer_collection.children:
        found = recurLayerCollection(layer, collection_name)
        if found:
            return found


def getViewLayerCollection(context, widget=None):
    widget_collection = bpy.data.collections[bpy.data.objects[widget.name].users_collection[0].name]
    # save current active layer_collection
    saved_layer_collection = bpy.context.view_layer.layer_collection
    # actually find the view_layer we want
    layer_collection = recurLayerCollection(
        saved_layer_collection, widget_collection.name)
    # make sure the collection (data level) is not hidden
    widget_collection.hide_viewport = False

    # change the active view layer
    bpy.context.view_layer.active_layer_collection = layer_collection
    # make sure it isn't excluded so it can be edited
    layer_collection.exclude = False
    # return the active view layer to what it was
    bpy.context.view_layer.active_layer_collection = saved_layer_collection

    return layer_collection


def boneMatrix(widget, matchBone):
    if widget == None:
        return
    widget.matrix_local = matchBone.bone.matrix_local
    widget.matrix_world = matchBone.id_data.matrix_world @ matchBone.bone.matrix_local
    if matchBone.custom_shape_transform:
        # if it has a tranform override apply this to the widget loc and rot
        org_scale = widget.matrix_world.to_scale()
        org_scale_mat = Matrix.Scale(1, 4, org_scale)
        target_matrix = matchBone.custom_shape_transform.id_data.matrix_world @ matchBone.custom_shape_transform.bone.matrix_local
        loc = target_matrix.to_translation()
        loc_mat = Matrix.Translation(loc)
        rot = target_matrix.to_euler().to_matrix()
        widget.matrix_world = loc_mat @ rot.to_4x4() @ org_scale_mat

    if matchBone.use_custom_shape_bone_size:
        ob_scale = bpy.context.scene.objects[matchBone.id_data.name].scale
        widget.scale = [matchBone.bone.length * ob_scale[0],
                        matchBone.bone.length * ob_scale[1], matchBone.bone.length * ob_scale[2]]
        #widget.scale = [matchBone.bone.length, matchBone.bone.length, matchBone.bone.length]
    widget.data.update()


def fromWidgetFindBone(widget):
    matchBone = None
    for ob in bpy.context.scene.objects:
        if ob.type == "ARMATURE":
            for bone in ob.pose.bones:
                if bone.custom_shape == widget:
                    matchBone = bone
    return matchBone


def createWidget(bone, widget, relative, size, scale, slide, rotation, collection):
    C = bpy.context
    D = bpy.data
    bw_widget_prefix = C.preferences.addons[__package__].preferences.widget_prefix

#     if bone.custom_shape_transform:
#    matrixBone = bone.custom_shape_transform
#     else:
    matrixBone = bone

    if bone.custom_shape:
        bone.custom_shape.name = bone.custom_shape.name + "_old"
        bone.custom_shape.data.name = bone.custom_shape.data.name + "_old"
        if C.scene.collection.objects.get(bone.custom_shape.name):
            C.scene.collection.objects.unlink(bone.custom_shape)

    # make the data name include the prefix
    newData = D.meshes.new(bw_widget_prefix + bone.name)

    if relative is True:
        boneLength = 1
    else:
        boneLength = (1 / bone.bone.length)

    # add the verts
    newData.from_pydata(numpy.array(widget['vertices']) * [size * scale[0] * boneLength, size * scale[2]
                                                           * boneLength, size * scale[1] * boneLength], widget['edges'], widget['faces'])

    # Create tranform matrices (slide vector and rotation)
    widget_matrix = Matrix()
    trans = Matrix.Translation((0, slide, 0))
    rot = rotation.to_matrix().to_4x4()

    # Translate then rotate the matrix
    widget_matrix = widget_matrix @ trans
    widget_matrix = widget_matrix @ rot

    # transform the widget with this matrix
    newData.transform(widget_matrix)

    newData.update(calc_edges=True)

    newObject = D.objects.new(bw_widget_prefix + bone.name, newData)

    newObject.data = newData
    newObject.name = bw_widget_prefix + bone.name
    collection.objects.link(newObject)

    newObject.matrix_world = bpy.context.active_object.matrix_world @ matrixBone.bone.matrix_local
    newObject.scale = [matrixBone.bone.length,
                       matrixBone.bone.length, matrixBone.bone.length]
    layer = bpy.context.view_layer
    layer.update()

    bone.custom_shape = newObject
    bone.bone.show_wire = True


def symmetrizeWidget(bone, collection):
    C = bpy.context
    D = bpy.data
    bw_widget_prefix = C.preferences.addons[__package__].preferences.widget_prefix

    widget = bone.custom_shape
    if findMirrorObject(bone) is not None:
        if findMirrorObject(bone).custom_shape_transform:
            mirrorBone = findMirrorObject(bone).custom_shape_transform
        else:
            mirrorBone = findMirrorObject(bone)

        mirrorWidget = mirrorBone.custom_shape
        if mirrorWidget:
            if mirrorWidget != widget:
                mirrorWidget.name = mirrorWidget.name + "_old"
                mirrorWidget.data.name = mirrorWidget.data.name + "_old"
                # unlink/delete old widget
                if C.scene.objects.get(mirrorWidget.name):
                    D.objects.remove(mirrorWidget)

        newData = widget.data.copy()
        for vert in newData.vertices:
            vert.co = numpy.array(vert.co) * (-1, 1, 1)

        newObject = widget.copy()
        newObject.data = newData
        newData.update()
        newObject.name = bw_widget_prefix + mirrorBone.name
        D.collections[collection.name].objects.link(newObject)
        newObject.matrix_local = mirrorBone.bone.matrix_local
        newObject.scale = [mirrorBone.bone.length,
                           mirrorBone.bone.length, mirrorBone.bone.length]

        layer = bpy.context.view_layer
        layer.update()

        mirrorBone.custom_shape = newObject
        mirrorBone.bone.show_wire = True

    else:
        pass


def symmetrizeWidget_helper(bone, collection, activeObject, widgetsAndBones):
    C = bpy.context

    bw_symmetry_suffix = C.preferences.addons[__package__].preferences.symmetry_suffix
    bw_symmetry_suffix = bw_symmetry_suffix.split(";")

    suffix_1 = bw_symmetry_suffix[0].replace(" ", "")
    suffix_2 = bw_symmetry_suffix[1].replace(" ", "")

    if activeObject.name.endswith(suffix_1):
        if bone.name.endswith(suffix_1) and widgetsAndBones[bone]:
            symmetrizeWidget(bone, collection)
    elif activeObject.name.endswith(suffix_2):
        if bone.name.endswith(suffix_2) and widgetsAndBones[bone]:
            symmetrizeWidget(bone, collection)


def deleteUnusedWidgets():
    C = bpy.context
    D = bpy.data

    bw_collection_name = C.preferences.addons[__package__].preferences.bonewidget_collection_name
    collection = recurLayerCollection(C.scene.collection, bw_collection_name)
    widgetList = []

    for ob in D.objects:
        if ob.type == 'ARMATURE':
            for bone in ob.pose.bones:
                if bone.custom_shape:
                    widgetList.append(bone.custom_shape)

    unwantedList = [
        ob for ob in collection.all_objects if ob not in widgetList]
    # save the current context mode
    mode = C.mode
    # jump into object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    # delete unwanted widgets
    bpy.ops.object.delete({"selected_objects": unwantedList})
    # jump back to current mode
    bpy.ops.object.mode_set(mode=mode)

    return unwantedList


def editWidget(active_bone):
    C = bpy.context
    D = bpy.data
    widget = active_bone.custom_shape

    armature = active_bone.id_data
    bpy.ops.object.mode_set(mode='OBJECT')
    C.active_object.select_set(False)

    collection = getViewLayerCollection(C, widget)
    collection.hide_viewport = False

    if C.space_data.local_view:
        bpy.ops.view3d.localview()

    # select object and make it active
    widget.select_set(True)
    bpy.context.view_layer.objects.active = widget
    bpy.ops.object.mode_set(mode='EDIT')


def returnToArmature(widget):
    C = bpy.context
    D = bpy.data

    bone = fromWidgetFindBone(widget)
    armature = bone.id_data

    if C.active_object.mode == 'EDIT':
        bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.select_all(action='DESELECT')

    collection = getViewLayerCollection(C, widget)
    collection.hide_viewport = True
    if C.space_data.local_view:
        bpy.ops.view3d.localview()
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')
    armature.data.bones[bone.name].select = True
    armature.data.bones.active = armature.data.bones[bone.name]


def findMirrorObject(object):
    C = bpy.context
    D = bpy.data

    bw_symmetry_suffix = C.preferences.addons[__package__].preferences.symmetry_suffix
    bw_symmetry_suffix = bw_symmetry_suffix.split(";")

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

    objectName = list(object.name)
    objectBaseName = objectName[:-suffix_length]
    mirroredObjectName = "".join(objectBaseName) + suffix

    if object.id_data.type == 'ARMATURE':
        return object.id_data.pose.bones.get(mirroredObjectName)
    else:
        return bpy.context.scene.objects.get(mirroredObjectName)


def findMatchBones():
    C = bpy.context
    D = bpy.data

    bw_symmetry_suffix = C.preferences.addons[__package__].preferences.symmetry_suffix
    bw_symmetry_suffix = bw_symmetry_suffix.split(";")

    suffix_1 = bw_symmetry_suffix[0].replace(" ", "")
    suffix_2 = bw_symmetry_suffix[1].replace(" ", "")

    widgetsAndBones = {}

    if bpy.context.object.type == 'ARMATURE':
        for bone in C.selected_pose_bones:
            if bone.name.endswith(suffix_1) or bone.name.endswith(suffix_2):
                widgetsAndBones[bone] = bone.custom_shape
                mirrorBone = findMirrorObject(bone)
                if mirrorBone:
                    widgetsAndBones[mirrorBone] = mirrorBone.custom_shape

        armature = bpy.context.object
        activeObject = C.active_pose_bone
    else:
        for shape in C.selected_objects:
            bone = fromWidgetFindBone(shape)
            if bone.name.endswith(("L", "R")):
                widgetsAndBones[fromWidgetFindBone(shape)] = shape

                mirrorShape = findMirrorObject(shape)
                if mirrorShape:
                    widgetsAndBones[mirrorShape] = mirrorShape

        activeObject = fromWidgetFindBone(C.object)
        armature = activeObject.id_data
    return (widgetsAndBones, activeObject, armature)


def resyncWidgetNames():
    C = bpy.context
    D = bpy.data

    bw_collection_name = C.preferences.addons[__package__].preferences.bonewidget_collection_name
    bw_widget_prefix = C.preferences.addons[__package__].preferences.widget_prefix

    widgetsAndBones = {}

    if bpy.context.object.type == 'ARMATURE':
        for bone in C.active_object.pose.bones:
            if bone.custom_shape:
                widgetsAndBones[bone] = bone.custom_shape

    for k, v in widgetsAndBones.items():
        if k.name != (bw_widget_prefix + k.name):
            D.objects[v.name].name = str(bw_widget_prefix + k.name)


def clearBoneWidgets():
    C = bpy.context
    D = bpy.data

    if bpy.context.object.type == 'ARMATURE':
        for bone in C.selected_pose_bones:
            if bone.custom_shape:
                bone.custom_shape = None
                bone.custom_shape_transform = None


def addObjectAsWidget(context, collection):
    sel = bpy.context.selected_objects
    #bw_collection = context.preferences.addons[__package__].preferences.bonewidget_collection_name

    if sel[1].type == 'MESH':
        active_bone = context.active_pose_bone
        widget_object = sel[1]

        # deal with any existing shape
        if active_bone.custom_shape:
            active_bone.custom_shape.name = active_bone.custom_shape.name + "_old"
            active_bone.custom_shape.data.name = active_bone.custom_shape.data.name + "_old"
            if context.scene.collection.objects.get(active_bone.custom_shape.name):
                context.scene.collection.objects.unlink(
                    active_bone.custom_shape)

        # duplicate shape
        widget = widget_object.copy()
        widget.data = widget.data.copy()
        # reamame it
        bw_widget_prefix = context.preferences.addons[__package__].preferences.widget_prefix
        widget_name = bw_widget_prefix + active_bone.name
        widget.name = widget_name
        widget.data.name = widget_name
        # link it
        collection.objects.link(widget)

        # match transforms
        widget.matrix_world = bpy.context.active_object.matrix_world @ active_bone.bone.matrix_local
        widget.scale = [active_bone.bone.length,
                        active_bone.bone.length, active_bone.bone.length]
        layer = bpy.context.view_layer
        layer.update()

        active_bone.custom_shape = widget
        active_bone.bone.show_wire = True

        # deselect original object
        widget_object.select_set(False)
