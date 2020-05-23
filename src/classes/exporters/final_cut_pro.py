"""
 @file
 @brief This file is used to generate a Final Cut Pro export
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

import os
from operator import itemgetter
from uuid import uuid1
from xml.dom import minidom

from PyQt5.QtWidgets import QFileDialog

from classes import info
from classes.app import get_app
from classes.logger import log
from classes.query import Clip, Track


def createEffect(xmldoc, name, node, points, scale):
    """Create the XML filter with keyframes"""
    # Find correct effect
    for effectNode in node.getElementsByTagName('effect'):
        effectName = effectNode.getElementsByTagName("name")[0].childNodes[0].nodeValue
        if effectName == name:
            parameterNode = effectNode.getElementsByTagName('parameter')[0]

            # Loop through Points (remove duplicates)
            keyframes = {}
            for point in points:
                keyframeTime = point.get('co', {}).get('X', 1)
                keyframeValue = point.get('co', {}).get('Y', 1) * scale
                keyframes[keyframeTime] = keyframeValue

            # Loop through Points
            first_value = None
            for keyframeTime in sorted(keyframes.keys()):
                keyframeValue = keyframes.get(keyframeTime)
                if first_value is None:
                    first_value = keyframeValue

                # Create keyframe element for each point
                keyframeNode = xmldoc.createElement("keyframe")
                parameterNode.appendChild(keyframeNode)
                whenNode = xmldoc.createElement("when")
                whenNode.appendChild(xmldoc.createTextNode(str(keyframeTime)))
                keyframeNode.appendChild(whenNode)
                valueNode = xmldoc.createElement("value")
                valueNode.appendChild(xmldoc.createTextNode(str(keyframeValue)))
                keyframeNode.appendChild(valueNode)


def export_xml():
    """Export final cut pro XML file"""
    app = get_app()
    _ = app._tr

    # Get FPS info
    fps_num = get_app().project.get("fps").get("num", 24)
    fps_den = get_app().project.get("fps").get("den", 1)
    fps_float = float(fps_num / fps_den)

    # Ticks (final cut pro value)
    ticks = 254016000000

    # Get path
    recommended_path = get_app().project.current_filepath or ""
    if not recommended_path:
        recommended_path = os.path.join(info.HOME_PATH, "%s.xml" % _("Untitled Project"))
    else:
        recommended_path = recommended_path.replace(".osp", ".xml")
    file_path = QFileDialog.getSaveFileName(app.window, _("Export XML..."), recommended_path,
                                            _("Final Cut Pro (*.xml)"))[0]
    if not file_path:
        # User canceled dialog
        return

    # Append .xml if needed
    if not file_path.endswith(".xml"):
        file_path = "%s.xml" % file_path

    # Get filename with no path
    file_name = os.path.basename(file_path)

    # Determine max frame (based on clips)
    duration = 0.0
    for clip in Clip.filter():
        clip_last_frame = clip.data.get("position") + (clip.data.get("end") - clip.data.get("start"))
        if clip_last_frame > duration:
            # Set max length of timeline
            duration = clip_last_frame

    # XML template path
    xmldoc = minidom.parse(os.path.join(info.RESOURCES_PATH, 'export-project-template.xml'))

    # Set Project Details
    xmldoc.getElementsByTagName("name")[0].childNodes[0].nodeValue = file_name
    xmldoc.getElementsByTagName("uuid")[0].childNodes[0].nodeValue = str(uuid1())
    xmldoc.getElementsByTagName("duration")[0].childNodes[0].nodeValue = duration
    xmldoc.getElementsByTagName("width")[0].childNodes[0].nodeValue = app.project.get("width")
    xmldoc.getElementsByTagName("height")[0].childNodes[0].nodeValue = app.project.get("height")
    xmldoc.getElementsByTagName("samplerate")[0].childNodes[0].nodeValue = app.project.get("sample_rate")
    xmldoc.getElementsByTagName("sequence")[0].setAttribute("id", app.project.get("id"))
    for childNode in xmldoc.getElementsByTagName("timebase"):
        childNode.childNodes[0].nodeValue = fps_float

    # Get parent audio node
    parentAudioNode = xmldoc.getElementsByTagName("audio")[0]

    # Loop through tracks
    all_tracks = get_app().project.get("layers")
    track_count = 1
    for track in sorted(all_tracks, key=itemgetter('number')):
        existing_track = Track.get(number=track.get("number"))
        if not existing_track:
            # Log error and fail silently, and continue
            log.error('No track object found with number: %s' % track.get("number"))
            continue

        # Track details
        track_locked = track.get("lock", False)
        clips_on_track = Clip.filter(layer=track.get("number"))
        if not clips_on_track:
            continue

        # Create video track node
        trackTemplateDoc = minidom.parse(os.path.join(info.RESOURCES_PATH, 'export-track-video-template.xml'))
        videoTrackNode = trackTemplateDoc.getElementsByTagName('track')[0]
        xmldoc.getElementsByTagName("video")[0].appendChild(videoTrackNode)

        # Create audio track nodes (1 for each channel)
        trackTemplateDoc = minidom.parse(os.path.join(info.RESOURCES_PATH, 'export-track-audio-template.xml'))
        audioTrackNode = trackTemplateDoc.getElementsByTagName('track')[0]
        parentAudioNode.appendChild(audioTrackNode)
        audioTrackNode.getElementsByTagName("outputchannelindex")[0].childNodes[0].nodeValue = track_count

        # Is Track Locked?
        if track_locked:
            videoTrackNode.getElementsByTagName("locked")[0].childNodes[0].nodeValue = "TRUE"
            audioTrackNode.getElementsByTagName("locked")[0].childNodes[0].nodeValue = "TRUE"

        # Loop through clips on this track
        for clip in clips_on_track:
            # Create VIDEO clip node
            clipNode = None
            if clip.data.get("reader", {}).get("has_video"):
                clipTemplateDoc = minidom.parse(os.path.join(info.RESOURCES_PATH, 'export-clip-video-template.xml'))
                clipNode = clipTemplateDoc.getElementsByTagName('clipitem')[0]
                videoTrackNode.appendChild(clipNode)

                # Update clip properties
                clipNode.setAttribute('id', clip.data.get('id'))
                clipNode.getElementsByTagName("file")[0].setAttribute('id', clip.data.get('file_id'))
                clipNode.getElementsByTagName("name")[0].childNodes[0].nodeValue = clip.data.get('title')
                clipNode.getElementsByTagName("name")[1].childNodes[0].nodeValue = clip.data.get('title')
                clipNode.getElementsByTagName("pathurl")[0].childNodes[0].nodeValue = clip.data.get('title')
                clipNode.getElementsByTagName("in")[0].childNodes[0].nodeValue = clip.data.get('start') * fps_float
                clipNode.getElementsByTagName("out")[0].childNodes[0].nodeValue = clip.data.get('end') * fps_float
                clipNode.getElementsByTagName("start")[0].childNodes[0].nodeValue = clip.data.get('position') * fps_float
                clipNode.getElementsByTagName("end")[0].childNodes[0].nodeValue = (clip.data.get('position') + (clip.data.get('end') - clip.data.get('start'))) * fps_float
                clipNode.getElementsByTagName("duration")[0].childNodes[0].nodeValue = (clip.data.get('end') - clip.data.get('start')) * fps_float
                clipNode.getElementsByTagName("pproTicksIn")[0].childNodes[0].nodeValue = (clip.data.get('start') * fps_float) * ticks
                clipNode.getElementsByTagName("pproTicksOut")[0].childNodes[0].nodeValue = (clip.data.get('end') * fps_float) * ticks

                # Add Keyframes (if any)
                createEffect(xmldoc, "Opacity", clipNode, clip.data.get('alpha', {}).get('Points', []), 100.0)

            # Create AUDIO clip nodes
            if clip.data.get("reader", {}).get("has_audio"):
                clipTemplateDoc = minidom.parse(os.path.join(info.RESOURCES_PATH, 'export-clip-audio-template.xml'))
                clipAudioNode = clipTemplateDoc.getElementsByTagName('clipitem')[0]
                audioTrackNode.appendChild(clipAudioNode)

                # Update audio characteristics
                if clipNode:
                    clipNode.getElementsByTagName("samplerate")[0].childNodes[0].nodeValue = clip.data.get("reader", {}).get("channels")
                    clipNode.getElementsByTagName("channelcount")[0].childNodes[0].nodeValue = clip.data.get("reader", {}).get("sample_rate")
                    clipAudioNode.getElementsByTagName("file")[0].childNodes.clear()
                else:
                    clipAudioNode.getElementsByTagName("name")[1].childNodes[0].nodeValue = clip.data.get('title')
                    clipAudioNode.getElementsByTagName("pathurl")[0].childNodes[0].nodeValue = clip.data.get('title')

                # Update audio clip properties
                clipAudioNode.setAttribute('id', "%s-audio" % clip.data.get('id'))
                clipAudioNode.getElementsByTagName("file")[0].setAttribute('id', clip.data.get('file_id'))
                clipAudioNode.getElementsByTagName("trackindex")[0].childNodes[0].nodeValue = track_count
                clipAudioNode.getElementsByTagName("name")[0].childNodes[0].nodeValue = clip.data.get('title')
                clipAudioNode.getElementsByTagName("in")[0].childNodes[0].nodeValue = clip.data.get('start') * fps_float
                clipAudioNode.getElementsByTagName("out")[0].childNodes[0].nodeValue = clip.data.get('end') * fps_float
                clipAudioNode.getElementsByTagName("start")[0].childNodes[0].nodeValue = clip.data.get('position') * fps_float
                clipAudioNode.getElementsByTagName("end")[0].childNodes[0].nodeValue = (clip.data.get('position') + (clip.data.get('end') - clip.data.get('start'))) * fps_float
                clipAudioNode.getElementsByTagName("duration")[0].childNodes[0].nodeValue = (clip.data.get('end') - clip.data.get('start')) * fps_float
                clipAudioNode.getElementsByTagName("pproTicksIn")[0].childNodes[0].nodeValue = (clip.data.get('start') * fps_float) * ticks
                clipAudioNode.getElementsByTagName("pproTicksOut")[0].childNodes[0].nodeValue = (clip.data.get('end') * fps_float) * ticks

                # Add Keyframes (if any)
                createEffect(xmldoc, "Audio Levels", clipAudioNode, clip.data.get('volume', {}).get('Points', []), 1.0)
            else:
                # No audio, remove audio characteristics
                if clipNode:
                    clipNode.getElementsByTagName("audio").pop()

        # Update counter
        track_count += 1

    try:
        file = open(os.fsencode(file_path), "wb")  # wb needed for windows support
        file.write(bytes(xmldoc.toxml(), 'UTF-8'))
        file.close()
    except IOError as inst:
        log.error("Error writing XML export: {}".format(str(inst)))
    finally:
        # Free up DOM memory
        xmldoc.unlink()
