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
    collection = context.scene.collection.children.get(bw_collection_name)
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


def getViewLayerCollection(context):
    bw_collection_name = context.preferences.addons[__package__].preferences.bonewidget_collection_name
    collection = context.view_layer.layer_collection.children[bw_collection_name]
    return collection


def boneMatrix(widget, matchBone):
    widget.matrix_local = matchBone.bone.matrix_local
    widget.matrix_world = matchBone.id_data.matrix_world @ matchBone.bone.matrix_local
    if matchBone.use_custom_shape_bone_size:
        widget.scale = [matchBone.bone.length,
                        matchBone.bone.length, matchBone.bone.length]
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

    # if bone.custom_shape_transform:
    #matrixBone = bone.custom_shape_transform
    # else:
    matrixBone = bone

    if bone.custom_shape:
        bone.custom_shape.name = bone.custom_shape.name+"_old"
        bone.custom_shape.data.name = bone.custom_shape.data.name+"_old"
        if C.scene.collection.objects.get(bone.custom_shape.name):
            C.scene.collection.objects.unlink(bone.custom_shape)

    # make the data name include the prefix
    newData = D.meshes.new(bw_widget_prefix + bone.name)

    if relative == True:
        boneLength = 1
    else:
        boneLength = (1/bone.bone.length)

    # add the verts
    newData.from_pydata(numpy.array(widget['vertices'])*[size*scale[0]*boneLength, size*scale[2]
                                                         * boneLength, size*scale[1]*boneLength], widget['edges'], widget['faces'])

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

    if findMirrorObject(bone).custom_shape_transform:
        mirrorBone = findMirrorObject(bone).custom_shape_transform
    else:
        mirrorBone = findMirrorObject(bone)

    mirrorWidget = mirrorBone.custom_shape

    if mirrorWidget:
        if mirrorWidget != widget:
            mirrorWidget.name = mirrorWidget.name+"_old"
            mirrorWidget.data.name = mirrorWidget.data.name+"_old"
            # unlink/delete old widget
            if C.scene.objects.get(mirrorWidget.name):
                D.objects.remove(mirrorWidget)

    newData = widget.data.copy()
    for vert in newData.vertices:
        vert.co = numpy.array(vert.co)*(-1, 1, 1)

    newObject = widget.copy()
    newObject.data = newData
    newData.update()
    newObject.name = bw_widget_prefix + mirrorBone.name
    collection.objects.link(newObject)
    newObject.matrix_local = mirrorBone.bone.matrix_local
    newObject.scale = [mirrorBone.bone.length,
                       mirrorBone.bone.length, mirrorBone.bone.length]

    layer = bpy.context.view_layer
    layer.update()

    mirrorBone.custom_shape = newObject
    mirrorBone.bone.show_wire = True


def deleteUnusedWidgets():
    C = bpy.context
    D = bpy.data

    bw_collection_name = C.preferences.addons[__package__].preferences.bonewidget_collection_name

    widgetList = []

    for ob in D.objects:
        if ob.type == 'ARMATURE':
            for bone in ob.pose.bones:
                if bone.custom_shape:
                    widgetList.append(bone.custom_shape)

    unwantedList = [
        ob for ob in C.scene.collection.children[bw_collection_name].all_objects if ob not in widgetList]
    # save the current context mode
    mode = C.mode
    # jump into object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    # delete unwanted widgets
    bpy.ops.object.delete({"selected_objects": unwantedList})
    # jump back to current mode
    bpy.ops.object.mode_set(mode=mode)


def editWidget(active_bone):
    C = bpy.context
    D = bpy.data
    widget = active_bone.custom_shape

    armature = active_bone.id_data
    bpy.ops.object.mode_set(mode='OBJECT')
    C.active_object.select_set(False)

    collection = getViewLayerCollection(C)
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

    collection = getViewLayerCollection(C)
    collection.hide_viewport = True
    if C.space_data.local_view:
        bpy.ops.view3d.localview()
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')
    armature.data.bones[bone.name].select = True
    armature.data.bones.active = armature.data.bones[bone.name]


def findMirrorObject(object):
    if object.name.endswith("L"):
        suffix = 'R'
    elif object.name.endswith("R"):
        suffix = 'L'
    elif object.name.endswith("l"):
        suffix = 'r'
    elif object.name.endswith("r"):
        suffix = 'l'
    else:  # what if the widget ends in .001?
        print('Object suffix unknown using blank')
        suffix = ''

    objectName = list(object.name)
    objectBaseName = objectName[:-1]
    mirroredObjectName = "".join(objectBaseName)+suffix

    if object.id_data.type == 'ARMATURE':
        return object.id_data.pose.bones.get(mirroredObjectName)
    else:
        return bpy.context.scene.objects.get(mirroredObjectName)


def findMatchBones():
    C = bpy.context
    D = bpy.data

    widgetsAndBones = {}

    if bpy.context.object.type == 'ARMATURE':
        for bone in C.selected_pose_bones:
            if bone.name.endswith("L") or bone.name.endswith("R"):
                widgetsAndBones[bone] = bone.custom_shape
                mirrorBone = findMirrorObject(bone)
                if mirrorBone:
                    widgetsAndBones[mirrorBone] = mirrorBone.custom_shape

        armature = bpy.context.object
        activeObject = C.active_pose_bone
    else:
        for shape in C.selected_objects:
            bone = fromWidgetFindBone(shape)
            if bone.name.endswith("L") or bone.name.endswith("R"):
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
