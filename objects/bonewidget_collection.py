import bpy

from bpy.types import (
    Collection,
    LayerCollection,
    Object,
    PoseBone,
)
import typing

from .. import custom_types

class BonewidgetCollection:
    def __init__(self, widget: 'Object' = None, layer_collection: bool = True) -> None:
        self.collection_name = self._get_collection_name()
        self.find_existing_widget_collection()

        if widget:
            self.collection_name = widget.users_collection[0].name

        start_collection = bpy.context.view_layer.layer_collection

        if not layer_collection:
            start_collection = bpy.context.scene.collection

        self.collection = self._recursively_find_layer_collection(start_collection)

    def find_existing_widget_collection(self) -> None:
        if not(bpy.context.active_object and  bpy.context.active_object.type == "ARMATURE"):
            return

        armature = bpy.context.active_object
        collection: 'Collection' = None
        collection_children: typing.List[str] = []

        for bone in armature.pose.bones:
            bone: 'PoseBone'

            if not bone.custom_shape:
                continue

            collection_children.append(bone.custom_shape.name)

            if not collection:
                collection = bone.custom_shape.users_collection[0]
                continue

            if collection.name != bone.custom_shape.users_collection[0].name:
                return

        if not collection:
            return

        for object in collection.objects:
            object: 'Object'

            if not (object.name in collection_children or object.name.find("_old") > 0):
                return

        self.collection_name = collection.name

    def create_collection(self) -> None:
        """Link a widget collection to the scene or create a new collection, if the widget collection doesn't exist.
        """

        collection = bpy.data.collections.get(self.collection_name)

        if collection:
            bpy.context.scene.collection.children.link(collection)
            self.collection = collection
            bpy.context.view_layer.layer_collection.children[self.collection_name].hide_viewport = True
            return

        collection = bpy.data.collections.new(self.collection_name)
        bpy.context.scene.collection.children.link(collection)

        bpy.context.view_layer.layer_collection.children[self.collection_name].hide_viewport = True
        self.collection = collection


    def make_collection_editable(self) -> None:
        """Ensure that a collection can be edited by ensuring that a collection is not hidden on a data level and not excluded in the view layer.
        """

        active_layer_collection: 'LayerCollection' = bpy.context.view_layer.layer_collection

        self.collection.collection.hide_viewport = False

        bpy.context.view_layer.active_layer_collection = self.collection
        self.collection.exclude = False
        bpy.context.view_layer.active_layer_collection = active_layer_collection


    def _recursively_find_layer_collection(self, collection: typing.Union['Collection', 'LayerCollection']) -> typing.Union['Collection', 'LayerCollection', None]:
        """Recursively find a collection with a specified collection name.

        Args:
            layer_collection (Collection): The collection to start searching from.

        Returns:
            Collection: The collection that has been searched for.
        """

        found: 'Collection' = None

        if collection.name == self.collection_name:
            return collection

        for c in collection.children:
            found = self._recursively_find_layer_collection(c)
            if found:
                return found


    def _get_collection_name(self) -> str:
        """Get the name of the widget collection.

        Returns:
            str: The name of the widget collection.
        """

        prefs: 'custom_types.AddonPreferences' = bpy.context.preferences.addons[__package__.split(".")[0]].preferences

        collection_name = prefs.bonewidget_collection_name

        if bpy.context.active_object:
            collection_name = collection_name.replace("{object}", bpy.context.active_object.name)

        return collection_name
