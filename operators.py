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
    Event,
    LayerCollection,
    Mesh,
    Object,
    Operator,
    OperatorProperties,
    PoseBone,
    UILayout
)
from bpy.props import (
    FloatProperty,
    BoolProperty,
    FloatVectorProperty,
    StringProperty
)

import numpy
from mathutils import Matrix

import typing

from .functions import (
    get_widget_prefix,
    read_widgets,
    object_data_to_dico,
    write_widgets
)

from .objects import (
    BonewidgetCollection
)

from .custom_types import (
    AddonPreferences
)


class BoneWidgetCreateBase(Operator):
    bl_options = {'REGISTER', 'UNDO'}

    relative_size: BoolProperty(
        name="Scale to Bone length",
        default=True,
        description="Scale Widget to bone length"
    )

    slide: FloatProperty(
        name="Slide",
        default=0.0,
        subtype='NONE',
        unit='NONE',
        description="Slide widget along y axis"
    )
    rotation: FloatVectorProperty(
        name="Rotation",
        description="Rotate the widget",
        default=(0.0, 0.0, 0.0),
        subtype='EULER',
        unit='ROTATION',
        precision=1,
    )
    scale: FloatVectorProperty(
        name="Scale",
        description="Scale of the widget",
        default=(1.0, 1.0, 1.0),
        subtype='XYZ',
    )

    @classmethod
    def poll(cls, context: 'Context'):
        return (context.object and context.object.mode == 'POSE')

    def draw(self, context: 'Context'):
        layout: 'UILayout' = self.layout
        layout.use_property_split = True
        col = layout.column()
        row = col.row(align=True)
        row.prop(self, "relative_size")
        row = col.row(align=True)
        row.prop(self, "scale", expand=False)
        row = col.row(align=True)
        row.prop(self, "slide")
        row = col.row(align=True)
        row.prop(self, "rotation", text="Rotation")

    def handle_existing_widget(self, bone: 'PoseBone'):
        if bone.custom_shape:
            bone.custom_shape.name = bone.custom_shape.name + "_old"
            bone.custom_shape.data.name = bone.custom_shape.data.name + "_old"
            if bpy.context.scene.collection.objects.get(bone.custom_shape.name):
                bpy.context.scene.collection.objects.unlink(bone.custom_shape)

    def update_widget_transforms(self, context: 'Context', widget_object: 'Object', matrix_bone: 'PoseBone'):
        widget_mesh: 'Mesh' = widget_object.data

        # Create tranform matrices (slide vector and rotation)
        widget_matrix = Matrix()
        trans = Matrix.Translation((0, self.slide, 0))
        rot = self.rotation.to_matrix().to_4x4()

        # Translate then rotate the matrix
        widget_matrix = widget_matrix @ trans
        widget_matrix = widget_matrix @ rot

        # transform the widget with this matrix
        widget_mesh.transform(widget_matrix)
        widget_mesh.update(calc_edges=True)

        widget_object.matrix_world = context.active_object.matrix_world @ matrix_bone.bone.matrix_local
        widget_object.scale = [matrix_bone.bone.length,
                               matrix_bone.bone.length, matrix_bone.bone.length]

        layer = context.view_layer
        layer.update()

    def add_mesh_data(self, mesh: 'Mesh', widget_data: dict, bone: 'PoseBone'):

        bone_length = 1
        if not self.relative_size:
            bone_length = 1 / bone.bone.length

        verticies = numpy.array(widget_data["vertices"]) * [
            self.scale[0] * bone_length,
            self.scale[2] * bone_length,
            self.scale[1] * bone_length
        ]

        mesh.from_pydata(verticies, widget_data['edges'], widget_data['faces'])


class BONEWIDGET_OT_create_widget(BoneWidgetCreateBase):
    """Creates a widget for selected bone"""
    bl_idname = "bonewidget.create_widget"
    bl_label = "Create"

    def execute(self, context: 'Context'):
        wgts = read_widgets()

        for bone in context.selected_pose_bones:
            bw_collection = BonewidgetCollection(layer_collection=False)
            if not bw_collection.collection:
                bw_collection.create_collection()

            self.create_widget(
                bone, wgts[context.scene.widget_list], bw_collection.collection)
        return {'FINISHED'}

    def create_widget(self, bone: 'PoseBone', widget: dict, collection: 'Collection'):
        """Create a widget for a bone.

        Args:
            bone (PoseBone): The bone to create the widget for.
            widget (dict): The JSON Data of the widget to create.
            collection (Collection): The collection to create the widget in.
        """

        context = bpy.context

        bw_widget_prefix = get_widget_prefix(context)
        widget_name = bw_widget_prefix + bone.name

        self.handle_existing_widget(bone)

        new_data = bpy.data.meshes.new(widget_name)
        self.add_mesh_data(new_data, widget, bone)

        new_object = bpy.data.objects.new(widget_name, new_data)
        new_object.data = new_data
        new_object.name = widget_name

        collection.objects.link(new_object)

        bone.custom_shape = new_object
        bone.bone.show_wire = True

        self.update_widget_transforms(context, new_object, bone)


class BONEWIDGET_OT_add_object_as_widget(BoneWidgetCreateBase):
    """Use an object from the scene as widget for the selected bone(s). Attention! Choosing objects with many vertices may cause Blender to freeze"""
    bl_idname = "bonewidget.add_as_widget"
    bl_label = "Use scene object"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: 'Context'):
        return context.object and context.object.mode == 'POSE' and len(context.selected_pose_bones) > 0

    def draw(self, context: 'Context'):
        layout: 'UILayout' = self.layout

        if self.status != "done":
            layout.label(text="Select an object from the scene:")
            layout.prop(context.scene, "widget_object", text="")
        else:
            super().draw(context)

    def invoke(self, context: 'Context', event: 'Event'):
        self.status = "adding"
        self.widget_object = None
        context.scene.widget_object = None
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context: 'Context'):
        self.status = "done"
        if not self.widget_object and context.scene.widget_object:
            self.widget_object = context.scene.widget_object

        if not self.widget_object:
            self.report({'WARNING'}, 'No object selected!')
            return {'CANCELLED'}

        for bone in context.selected_pose_bones:
            self.add_object_as_widget(context, bone)

        return {'FINISHED'}

    def add_object_as_widget(self, context: 'Context', bone: 'PoseBone'):
        bw_collection = BonewidgetCollection(layer_collection=False)
        if not bw_collection.collection:
            bw_collection.create_collection()

        collection = bw_collection.collection
        widget_object: 'Object' = self.widget_object

        bw_widget_prefix = get_widget_prefix(context)
        widget_name = bw_widget_prefix + bone.name

        self.handle_existing_widget(bone)

        widget_data = object_data_to_dico(context, widget_object)
        new_data = bpy.data.meshes.new(widget_name)
        self.add_mesh_data(new_data, widget_data, bone)

        widget: 'Object' = bpy.data.objects.new(widget_name, new_data)
        widget.data = new_data
        widget.name = widget_name

        collection.objects.link(widget)

        bone.custom_shape = widget
        bone.bone.show_wire = True

        self.update_widget_transforms(context, widget, bone)


class BONEWIDGET_OT_edit_widget(Operator):
    """Edit the widget for selected bone"""
    bl_idname = "bonewidget.edit_widget"
    bl_label = "Edit"

    @classmethod
    def poll(cls, context: 'Context'):
        return (context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE'
                and context.active_pose_bone and context.active_pose_bone.custom_shape is not None)

    def execute(self, context: 'Context'):
        active_bone = context.active_pose_bone
        try:
            self.edit_widget(active_bone)
        except KeyError:
            self.report(
                {'INFO'}, 'This widget is the not in the Widget Collection')
        return {'FINISHED'}

    def edit_widget(self, active_bone: 'PoseBone'):
        """Jump to edit mode for editing the widget of the active bone.

        Args:
            active_bone (PoseBone): The active bone.
        """

        context = bpy.context
        widget: 'Object' = active_bone.custom_shape

        armature = active_bone.id_data
        bpy.ops.object.mode_set(mode='OBJECT')
        context.active_object.select_set(False)

        bw_collection = BonewidgetCollection(widget=widget)
        bw_collection.make_collection_editable()

        collection: 'LayerCollection' = bw_collection.collection
        collection.hide_viewport = False

        if context.space_data.local_view:
            bpy.ops.view3d.localview()

        # select object and make it active
        widget.select_set(True)
        context.view_layer.objects.active = widget
        bpy.ops.object.mode_set(mode='EDIT')


class BONEWIDGET_OT_return_to_armature(Operator):
    """Switch back to the armature"""
    bl_idname = "bonewidget.return_to_armature"
    bl_label = "Return to armature"

    @classmethod
    def poll(cls, context: 'Context'):
        if not (context.object and context.object.type == 'MESH'
                and context.object.mode in ['EDIT', 'OBJECT']):
            return False
        return cls.from_widget_find_bone(context.object)

    @classmethod
    def from_widget_find_bone(cls, widget: 'Object') -> 'PoseBone':
        """Given an object, try to find the bone that the object is a custom widget of.
        If the object is a custom widget of multiple bones, the last occurence will be returned.

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

    def execute(self, context: 'Context'):
        widget: 'Object' = context.object

        bone: 'PoseBone' = self.from_widget_find_bone(widget)
        armature: 'Armature' = bone.id_data

        if context.active_object.mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.select_all(action='DESELECT')

        bw_collection = BonewidgetCollection(widget=widget)
        bw_collection.make_collection_editable()

        collection = bw_collection.collection
        collection.hide_viewport = True
        if context.space_data.local_view:
            bpy.ops.view3d.localview()
        context.view_layer.objects.active = armature
        armature.select_set(True)
        bpy.ops.object.mode_set(mode='POSE')
        armature.data.bones[bone.name].select = True
        armature.data.bones.active = armature.data.bones[bone.name]

        return {'FINISHED'}


class BONEWIDGET_OT_match_bone_transforms(Operator):
    """Match the widget to the bone transforms"""
    bl_idname = "bonewidget.match_bone_transforms"
    bl_label = "Match bone transforms"

    @classmethod
    def poll(cls, context: 'Context'):
        return context.mode == "POSE"

    def execute(self, context: 'Context'):
        for bone in context.selected_pose_bones:
            self.bone_matrix(context, bone.custom_shape, bone)

        return {'FINISHED'}

    def bone_matrix(self, context: 'Context', widget: 'Object', match_bone: 'PoseBone'):
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


class BONEWIDGET_OT_match_symmetrize_shape(Operator):
    """Symmetrize the widget of the selected bone to the opposite side"""
    bl_idname = "bonewidget.symmetrize_shape"
    bl_label = "Symmetrize"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def advanced_poll(cls, context: 'Context') -> typing.Tuple[bool, str]:
        """Helper function for the poll and description class methods.

        Args:
            context (Context): The current Blender context

        Returns:
            typing.Tuple[bool, str]: Whether the Operator can be executed, paired with a message, that provides further information.
        """

        prefs: 'AddonPreferences' = context.preferences.addons[__package__].preferences

        if not (context.object and context.object.type == "ARMATURE"):
            return (False, "This feature only works in pose mode")

        if not context.object.mode in ['POSE']:
            return (False, "This feature only works in pose mode")

        bone: 'PoseBone' = context.active_pose_bone

        if not bone or bone.custom_shape is None:
            return (False, "This feature only works for bones with widgets")

        bw_symmetry_suffix = prefs.symmetry_suffix.split(";")

        suffix_1 = bw_symmetry_suffix[0].replace(" ", "")
        suffix_2 = bw_symmetry_suffix[1].replace(" ", "")

        if bone.name.endswith(suffix_1) or bone.name.endswith(suffix_2):
            return (True, "")

        return (False, f"This feature only works if the bone ends with '{suffix_1}' or '{suffix_2}'")

    @classmethod
    def poll(cls, context: 'Context'):
        return cls.advanced_poll(context)[0]

    @classmethod
    def description(cls, context: 'Context', properties: 'OperatorProperties') -> str:
        passes_poll, msg = cls.advanced_poll(context)

        if passes_poll:
            return "Symmetrize the widget of the selected bone to the opposite side"

        return f"Symmetrize widget to the opposite side. {msg}"

    def execute(self, context: 'Context'):
        active_bone: 'PoseBone' = context.active_pose_bone
        widget = active_bone.custom_shape

        bw_collection = BonewidgetCollection(widget=widget)
        bw_collection.make_collection_editable()

        widget_collection: 'LayerCollection' = bw_collection.collection

        mirror_bone: 'PoseBone' = self.find_mirror_object(active_bone)
        if not mirror_bone:
            self.report({"WARNING"}, "No Bone to mirror to!")
            return {'FINISHED'}

        if mirror_bone.custom_shape_transform:
            mirror_bone = mirror_bone.custom_shape_transform

        mirror_widget: 'Object' = mirror_bone.custom_shape

        if mirror_widget is not None and mirror_widget != widget:
            mirror_widget.name = mirror_widget.name + "_old"
            mirror_widget.data.name = mirror_widget.data.name + "_old"
            # unlink/delete old widget
            if context.scene.objects.get(mirror_widget.name):
                bpy.data.objects.remove(mirror_widget)

        new_data = widget.data.copy()
        for vert in new_data.vertices:
            vert.co = numpy.array(vert.co) * (-1, 1, 1)

        new_object: 'Object' = widget.copy()
        new_object.name = get_widget_prefix(context) + mirror_bone.name
        new_object.data = new_data
        new_data.update()

        bpy.data.collections[widget_collection.name].objects.link(new_object)
        new_object.matrix_local = mirror_bone.bone.matrix_local
        new_object.scale = [mirror_bone.bone.length,
                            mirror_bone.bone.length, mirror_bone.bone.length]

        layer = context.view_layer
        layer.update()

        mirror_bone.custom_shape = new_object
        mirror_bone.bone.show_wire = True

        return {'FINISHED'}

    def find_mirror_object(self, object: 'Object') -> typing.Union['Object', 'PoseBone']:
        """Find the object that, according to the name and suffix, can be used for mirroring widgets.

        Args:
            object (Object): The object that should be mirrored from.

        Returns:
            typing.Union['Object', 'PoseBone']: The object that can be used for mirroring widgets.
        """

        context = bpy.context
        D = bpy.data

        prefs: 'AddonPreferences' = context.preferences.addons[
            __package__].preferences

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


class BONEWIDGET_OT_add_widgets(Operator):
    """Add the active object to the Bone Widget Library"""
    bl_idname = "bonewidget.add_widgets"
    bl_label = "Add to Widget library"

    widget_name: StringProperty(
        name="Widget Name",
        options={"TEXTEDIT_UPDATE"},
    )

    @classmethod
    def description(cls, context: 'Context', properties: 'OperatorProperties'):
        if context.mode == "POSE":
            return "Add the custom shape of the active bone to the Bone Widget Library"

        return "Add the active object to the Bone Widget Library"

    @classmethod
    def poll(cls, context: 'Context'):
        if context.mode == "POSE":
            return context.active_pose_bone is not None and context.active_pose_bone.custom_shape is not None

        return (context.object and context.object.type == 'MESH' and context.object.mode == 'OBJECT'
                and context.active_object is not None)

    def invoke(self, context: 'Context', event: 'Event'):
        self.widget_object: 'Object' = context.active_object

        if context.mode == "POSE":
            self.widget_object = context.active_pose_bone.custom_shape

        if not self.widget_object:
            self.report({'WARNING'}, 'No object or pose bone selected.')
            return {'FINISHED'}

        self.widget_name = self.widget_object.name.removeprefix(
            get_widget_prefix(context))

        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context: 'Context'):
        layout: 'UILayout' = self.layout
        layout.label(text="Widget Name:")
        layout.prop(self, "widget_name", text="")

    def execute(self, context: 'Context'):
        wgts: dict = read_widgets()

        widget_names: typing.List[str] = [k for k in wgts.keys()]

        if self.widget_name in widget_names:
            self.report(
                {'WARNING'}, f"A widget called '{self.widget_name}' already exists!")
            return {'FINISHED'}

        widget_names.append(self.widget_name)
        wgts[self.widget_name] = object_data_to_dico(
            context, self.widget_object)

        write_widgets(wgts)

        context.scene.widget_list = self.widget_name
        return {'FINISHED'}


class BONEWIDGET_OT_remove_widgets(Operator):
    """Remove selected widget from the Bone Widget Library"""
    bl_idname = "bonewidget.remove_widgets"
    bl_label = "Remove Widgets"

    def execute(self, context: 'Context'):
        wgts: dict = read_widgets()

        target_widget = context.scene.widget_list

        wgts.pop(target_widget, "")
        write_widgets(wgts)

        return {'FINISHED'}


class BONEWIDGET_OT_toggle_collection_visibility(Operator):
    """Show/hide the bone widget collection"""
    bl_idname = "bonewidget.toggle_collection_visibilty"
    bl_label = "Collection Visibilty"

    @classmethod
    def poll(cls, context: 'Context'):
        return (context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE')

    def execute(self, context: 'Context'):
        bw_collection: 'LayerCollection' = BonewidgetCollection().collection

        hidden = not bw_collection.hide_viewport

        # bw_collection = context.scene.collection.children.get(bw_collection_name)
        bw_collection.hide_viewport = hidden
        bw_collection.collection.hide_viewport = hidden

        # need to recursivly search for the view_layer
        bw_collection.exclude = False

        return {'FINISHED'}


class BONEWIDGET_OT_delete_unused_widgets(Operator):
    """Delete unused objects in the WGT collection"""
    bl_idname = "bonewidget.delete_unused_widgets"
    bl_label = "Delete Unused Widgets"

    @classmethod
    def poll(cls, context: 'Context'):
        return (context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE')

    def execute(self, context: 'Context'):
        D = bpy.data

        collection: 'Collection' = BonewidgetCollection(
            layer_collection=False).collection
        widget_list: list = []

        for ob in D.objects:
            ob: 'Object'
            if ob.type != 'ARMATURE':
                continue

            for bone in ob.pose.bones:
                bone: 'PoseBone'
                if bone.custom_shape:
                    widget_list.append(bone.custom_shape)

        unwanted_list = [
            ob for ob in collection.all_objects if ob not in widget_list]

        mode = context.mode
        bpy.ops.object.mode_set(mode='OBJECT')

        # Support breaking API change in Blender 3.2+
        if bpy.app.version >= (3, 2):
            context_override = context.copy()
            context_override["selected_objects"] = unwanted_list
            with context.temp_override(**context_override):
                bpy.ops.object.delete()
        else:
            bpy.ops.object.delete({"selected_objects": unwanted_list})

        bpy.ops.object.mode_set(mode=mode)

        return {'FINISHED'}


class BONEWIDGET_OT_clear_bone_widgets(Operator):
    """Clear widgets from selected pose bones"""
    bl_idname = "bonewidget.clear_widgets"
    bl_label = "Clear Widgets"

    @classmethod
    def poll(cls, context: 'Context'):
        return (context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE')

    def execute(self, context: 'Context'):
        if context.object.type != 'ARMATURE':
            return {'FINISHED'}

        for bone in context.selected_pose_bones:
            if bone.custom_shape:
                bone.custom_shape = None
                bone.custom_shape_transform = None

        return {'FINISHED'}


class BONEWIDGET_OT_resync_widget_names(Operator):
    """Sync widget names with the names of the bones they're assigned to."""
    bl_idname = "bonewidget.resync_widget_names"
    bl_label = "Resync Widget Names"

    @classmethod
    def poll(cls, context: 'Context'):
        return (context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE')

    def execute(self, context: 'Context'):

        D = bpy.data

        # bw_collection_name: str = get_collection_name(context)
        bw_widget_prefix: str = get_widget_prefix(context)

        widgets_and_bones: dict = {}

        # if context.object.type != 'ARMATURE':
        #     return {'FINISHED'}

        for bone in context.active_object.pose.bones:
            bone: 'PoseBone'
            if bone.custom_shape:
                widgets_and_bones[bone] = bone.custom_shape

        for bone, widget in widgets_and_bones.items():
            # ! This always returns True
            if bone.name != (bw_widget_prefix + bone.name):
                D.objects[widget.name].name = str(
                    bw_widget_prefix + bone.name)

        return {'FINISHED'}


classes = (
    BONEWIDGET_OT_remove_widgets,
    BONEWIDGET_OT_add_widgets,
    BONEWIDGET_OT_add_object_as_widget,
    BONEWIDGET_OT_match_symmetrize_shape,
    BONEWIDGET_OT_match_bone_transforms,
    BONEWIDGET_OT_return_to_armature,
    BONEWIDGET_OT_edit_widget,
    BONEWIDGET_OT_create_widget,
    BONEWIDGET_OT_toggle_collection_visibility,
    BONEWIDGET_OT_delete_unused_widgets,
    BONEWIDGET_OT_clear_bone_widgets,
    BONEWIDGET_OT_resync_widget_names,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
