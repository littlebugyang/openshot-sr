"""
 @file
 @brief This file is for legacy support of OpenShot 1.x project files
 @author Jonathan Thomas <jonathan@openshot.org>

 @section LICENSE

 Copyright (c) 2008-2018 OpenShot Studios, LLC
 (http://www.openshotstudios.com). This file is part of
 OpenShot Video Editor (http://www.openshot.org), an open-source project
 dedicated to delivering high quality video editing and animation solutions
 to the world.

 OpenShot Video Editor is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 OpenShot Video Editor is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with OpenShot Library.  If not, see <http://www.gnu.org/licenses/>.
 """

import uuid


class effect:
    """This class represents a media clip on the timeline."""

    # ----------------------------------------------------------------------
    def __init__(self, service, paramaters=[]):
        """Constructor"""

        # init variables for clip object
        self.service = service  # the name of the mlt service (i.e. frei0r.water, chroma, sox, etc...)
        self.paramaters = paramaters  # example:  "key" : "123123123",   "variance" : "0.15" (dictionary of settings)
        self.audio_effect = ""
        self.unique_id = str(uuid.uuid1())
