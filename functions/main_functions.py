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

from bpy.types import (
    Context
)


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
    prefs: 'custom_types.AddonPreferences' = context.preferences.addons[__package__].preferences

    prefix = prefs.widget_prefix

    if context.active_object:
        prefix = prefix.replace("{object}", context.active_object.name)

    return prefix

