'''
Copied and modified by littlebugyang based on openshot-qt.
'''
import os
import time

from classes import info
from classes import ui_util
from classes import settings
from classes.app import get_app
from classes.logger import log
from classes.metrics import track_metric_screen, track_metric_error

from PyQt5.QtWidgets import (
    QMessageBox, QDialog, QFileDialog, QDialogButtonBox, QPushButton
)

import openshot
import json

class SuperResolution(QDialog):
    # 可以看作是 SuperResolution 这一功能在 MVC 模式中的 Controller
    # TODO: 为什么不在 __init__ 里面 load ui
    # TODO: 为什么 .ui 文件的命名中不使用下划线而使用横杠

    ui_path = os.path.join(info.PATH, 'windows', 'ui', 'super-resolution.ui')

    def __init__(self):

        # Create dialog class
        QDialog.__init__(self)

        # Load UI from designer
        ui_util.load_ui(self, self.ui_path)

        # Init UI
        ui_util.init_ui(self)

        # get translations
        _ = get_app()._tr

        # Get settings
        self.s = settings.get_settings()

        # 绑定 cancel 按钮和 cancel 函数
        self.cancel_btn.clicked.connect(self.cancel)

        # 绑定 upload 按钮和 uploadSequence 函数
        self.upload_btn.clicked.connect(self.uploadSequence)

        # 保存当前可用的视频片段为类内所有
        self.avail_clips = get_app().window.timeline_sync.timeline.Clips()

        # Get the original timeline settings
        width = get_app().window.timeline_sync.timeline.info.width
        height = get_app().window.timeline_sync.timeline.info.height
        fps = get_app().window.timeline_sync.timeline.info.fps
        sample_rate = get_app().window.timeline_sync.timeline.info.sample_rate
        channels = get_app().window.timeline_sync.timeline.info.channels
        channel_layout = get_app().window.timeline_sync.timeline.info.channel_layout

        # Create new "export" openshot.Timeline object
        self.timeline = openshot.Timeline(width, height, openshot.Fraction(fps.num, fps.den),
                                          sample_rate, channels, channel_layout)
        # Init various properties
        self.timeline.info.channel_layout = get_app().window.timeline_sync.timeline.info.channel_layout
        self.timeline.info.has_audio = get_app().window.timeline_sync.timeline.info.has_audio
        self.timeline.info.has_video = get_app().window.timeline_sync.timeline.info.has_video
        self.timeline.info.video_length = get_app().window.timeline_sync.timeline.info.video_length
        self.timeline.info.duration = get_app().window.timeline_sync.timeline.info.duration
        self.timeline.info.sample_rate = get_app().window.timeline_sync.timeline.info.sample_rate
        self.timeline.info.channels = get_app().window.timeline_sync.timeline.info.channels

        # Load the "export" Timeline reader with the JSON from the real timeline
        json_timeline = json.dumps(get_app().project._data)
        self.timeline.SetJson(json_timeline)

        # Open the "export" Timeline reader
        self.timeline.Open()

        self.updateFrameRate()

    def updateFrameRate(self):
        """Callback for changing the frame rate"""
        # Adjust the main timeline reader
        # self.timeline.info.width = self.txtWidth.value()
        # self.timeline.info.height = self.txtHeight.value()
        # self.timeline.info.fps.num = self.txtFrameRateNum.value()
        # self.timeline.info.fps.den = self.txtFrameRateDen.value()
        # self.timeline.info.sample_rate = self.txtSampleRate.value()
        # self.timeline.info.channels = self.txtChannels.value()
        # self.timeline.info.channel_layout = self.cboChannelLayout.currentData()

        # Send changes to libopenshot (apply mappings to all framemappers)... after a small delay
        # self.delayed_fps_timer.start()

        # Determine max frame (based on clips)
        timeline_length = 0.0
        # 获取时间线的帧数
        fps = self.timeline.info.fps.ToFloat()
        # 获取时间线上的视频片段
        clips = self.timeline.Clips()
        for clip in clips:
            clip_last_frame = clip.Position() + clip.Duration()
            if clip_last_frame > timeline_length:
                # Set max length of timeline
                timeline_length = clip_last_frame

        # Convert to int and round
        self.timeline_length_int = round(timeline_length * fps) + 1

        # Set the min and max frame numbers for this project
        # self.txtStartFrame.setValue(1)
        # self.txtEndFrame.setValue(self.timeline_length_int)

        # Calculate differences between editing/preview FPS and export FPS
        current_fps = get_app().project.get("fps")
        current_fps_float = float(current_fps["num"]) / float(current_fps["den"])
        new_fps_float = float(25) / float(1)
        self.export_fps_factor = new_fps_float / current_fps_float
        self.original_fps_factor = current_fps_float / new_fps_float

    def uploadSequence(self):
        """ Start exporting video """

        # get translations
        _ = get_app()._tr

        # Init progress bar
        # 应该仅仅是用来展示进度条
        # self.progressExportVideo.setMinimum(self.txtStartFrame.value())
        # self.progressExportVideo.setMaximum(self.txtEndFrame.value())
        # self.progressExportVideo.setValue(self.txtStartFrame.value())

        # 这个是默认的图片文件输出格式
        self.image_format = "-%05d.png"

        export_type = _("Image Sequence")

        # Determine final exported file path (and replace blank paths with default ones)
        default_filename = "IM"
        default_folder = os.path.join(info.HOME_PATH, 'Desktop/temp')
        # 如果要导出图片序列，就规定好导出文件的命名
        file_name_with_ext = "%s%s" % (default_filename, self.image_format.strip())

        # 确定导出文件的路径
        export_file_path = os.path.join(default_folder, file_name_with_ext)
        log.info("锁定了的文件保存路径: %s" % export_file_path)

        # Init export settings
        # 以下的设定全部都已经写死了
        video_settings = {"vformat": 'mp4',
                          "vcodec": 'libx264',
                          "fps": {"num": 25, "den": 1},
                          "width": 1024,
                          "height": 576,
                          "pixel_ratio": {"num": 1, "den": 1},
                          "video_bitrate": 15000000,
                          "start_frame": 1,
                          "end_frame": 17
                          }

        audio_settings = {"acodec": 'aac',
                          "sample_rate": 48000,
                          "channels": 2,
                          "channel_layout": 3,
                          "audio_bitrate": 192000
                          }

        # Override vcodec and format for Image Sequences
        image_ext = os.path.splitext(self.image_format.strip())[1].replace(".", "")
        video_settings["vformat"] = image_ext
        if image_ext in ["jpg", "jpeg"]:
            video_settings["vcodec"] = "mjpeg"
        else:
            video_settings["vcodec"] = image_ext

        # Store updated export folder path in project file
        get_app().updates.update_untracked(["export_path"], os.path.dirname(export_file_path))
        # Mark project file as unsaved
        get_app().project.has_unsaved_changes = True

        # Set MaxSize (so we don't have any downsampling)
        self.timeline.SetMaxSize(video_settings.get("width"), video_settings.get("height"))

        # Set lossless cache settings (temporarily)
        export_cache_object = openshot.CacheMemory(500)
        self.timeline.SetCache(export_cache_object)

        # Rescale all keyframes (if needed)
        if self.export_fps_factor != 1.0:
            log.info("导出文件fps因子不为1")
            # Get a copy of rescaled project data (this does not modify the active project)
            rescaled_app_data = get_app().project.rescale_keyframes(self.export_fps_factor)

            # Load the "export" Timeline reader with the JSON from the real timeline
            self.timeline.SetJson(json.dumps(rescaled_app_data))

            # Re-update the timeline FPS again (since the timeline just got clobbered)
            self.updateFrameRate()

        # Create FFmpegWriter
        try:
            w = openshot.FFmpegWriter(export_file_path)

            # Set video options
            if export_type in [_("Video & Audio"), _("Video Only"), _("Image Sequence")]:
                w.SetVideoOptions(True,
                                  video_settings.get("vcodec"),
                                  openshot.Fraction(video_settings.get("fps").get("num"),
                                                    video_settings.get("fps").get("den")),
                                  video_settings.get("width"),
                                  video_settings.get("height"),
                                  openshot.Fraction(video_settings.get("pixel_ratio").get("num"),
                                                    video_settings.get("pixel_ratio").get("den")),
                                  False,
                                  False,
                                  video_settings.get("video_bitrate"))

            # Prepare the streams
            w.PrepareStreams()

            # These extra options should be set in an extra method
            # No feedback is given to the user
            # TODO: Tell user if option is not available
            # Muxing options for mp4/mov
            w.SetOption(openshot.VIDEO_STREAM, "muxing_preset", "mp4_faststart")
            # Set the quality in case crf was selected
            # if "crf" in self.txtVideoBitRate.text():
            #     w.SetOption(openshot.VIDEO_STREAM, "crf", str(int(video_settings.get("video_bitrate"))))
            # # Set the quality in case qp was selected
            # if "qp" in self.txtVideoBitRate.text():
            #     w.SetOption(openshot.VIDEO_STREAM, "qp", str(int(video_settings.get("video_bitrate"))))

            # Open the writer
            w.Open()

            # Notify window of export started
            title_message = ""
            get_app().window.ExportStarted.emit(export_file_path, video_settings.get("start_frame"),
                                                video_settings.get("end_frame"))

            progressstep = max(1, round((video_settings.get("end_frame") - video_settings.get("start_frame")) / 1000))
            start_time_export = time.time()
            start_frame_export = video_settings.get("start_frame")
            end_frame_export = video_settings.get("end_frame")
            # Write each frame in the selected range
            # 接下来就是导出动作的重要内容
            for frame in range(video_settings.get("start_frame"), video_settings.get("end_frame") + 1):
                # Update progress bar (emit signal to main window)
                if (frame % progressstep) == 0:
                    end_time_export = time.time()
                    if (((frame - start_frame_export) != 0) & ((end_time_export - start_time_export) != 0)):
                        seconds_left = round((start_time_export - end_time_export) * (frame - end_frame_export) / (
                                frame - start_frame_export))
                        fps_encode = ((frame - start_frame_export) / (end_time_export - start_time_export))
                        title_message = _("%(hours)d:%(minutes)02d:%(seconds)02d Remaining (%(fps)5.2f FPS)") % {
                            'hours': seconds_left / 3600,
                            'minutes': (seconds_left / 60) % 60,
                            'seconds': seconds_left % 60,
                            'fps': fps_encode}

                    # Emit frame exported
                    # get_app().window.ExportFrame.emit(title_message, video_settings.get("start_frame"), video_settings.get("end_frame"), frame)

                    # Process events (to show the progress bar moving)
                    # QCoreApplication.processEvents()

                # Write the frame object to the video
                w.WriteFrame(self.timeline.GetFrame(frame))

                # Check if we need to bail out
                # if not self.exporting:
                #     break

            # Close writer
            w.Close()

            # 下面的内容应该都是配合进度提示的，删除
            '''
            # Emit final exported frame (with elapsed time)
            seconds_run = round((end_time_export - start_time_export))
            title_message = _("%(hours)d:%(minutes)02d:%(seconds)02d Elapsed (%(fps)5.2f FPS)") % {
                'hours': seconds_run / 3600,
                'minutes': (seconds_run / 60) % 60,
                'seconds': seconds_run % 60,
                'fps': fps_encode}

            get_app().window.ExportFrame.emit(title_message, video_settings.get("start_frame"), video_settings.get("end_frame"), frame)
            '''

        except Exception as e:
            # TODO: Find a better way to catch the error. This is the only way I have found that
            # does not throw an error
            error_type_str = str(e)
            log.info("Error type string: %s" % error_type_str)

            if "InvalidChannels" in error_type_str:
                log.info("Error setting invalid # of channels (%s)" % (audio_settings.get("channels")))
                track_metric_error("invalid-channels-%s-%s-%s-%s" % (
                video_settings.get("vformat"), video_settings.get("vcodec"), audio_settings.get("acodec"),
                audio_settings.get("channels")))

            elif "InvalidSampleRate" in error_type_str:
                log.info("Error setting invalid sample rate (%s)" % (audio_settings.get("sample_rate")))
                track_metric_error("invalid-sample-rate-%s-%s-%s-%s" % (
                video_settings.get("vformat"), video_settings.get("vcodec"), audio_settings.get("acodec"),
                audio_settings.get("sample_rate")))

            elif "InvalidFormat" in error_type_str:
                log.info("Error setting invalid format (%s)" % (video_settings.get("vformat")))
                track_metric_error("invalid-format-%s" % (video_settings.get("vformat")))

            elif "InvalidCodec" in error_type_str:
                log.info("Error setting invalid codec (%s/%s/%s)" % (
                video_settings.get("vformat"), video_settings.get("vcodec"), audio_settings.get("acodec")))
                track_metric_error("invalid-codec-%s-%s-%s" % (
                video_settings.get("vformat"), video_settings.get("vcodec"), audio_settings.get("acodec")))

            elif "ErrorEncodingVideo" in error_type_str:
                log.info("Error encoding video frame (%s/%s/%s)" % (
                video_settings.get("vformat"), video_settings.get("vcodec"), audio_settings.get("acodec")))
                track_metric_error("video-encode-%s-%s-%s" % (
                video_settings.get("vformat"), video_settings.get("vcodec"), audio_settings.get("acodec")))

            # Show friendly error
            friendly_error = error_type_str.split("> ")[0].replace("<", "")

            # Prompt error message
            msg = QMessageBox()
            msg.setWindowTitle(_("Export Error"))
            msg.setText(_("Sorry, there was an error exporting your video: \n%s") % friendly_error)
            msg.exec_()

        # Notify window of export started
        get_app().window.ExportEnded.emit(export_file_path)

        # Close timeline object
        self.timeline.Close()

        # Clear all cache
        self.timeline.ClearAllCache()

        # Re-set OMP thread enabled flag
        if self.s.get("omp_threads_enabled"):
            openshot.Settings.Instance().WAIT_FOR_VIDEO_PROCESSING_TASK = False
        else:
            openshot.Settings.Instance().WAIT_FOR_VIDEO_PROCESSING_TASK = True

        # Return scale mode to lower quality scaling (for faster previews)
        openshot.Settings.Instance().HIGH_QUALITY_SCALING = False

        # Handle end of export (for non-canceled exports)
        # if self.s.get("show_finished_window") and self.exporting:
        #     # Hide cancel and export buttons
        #     self.cancel_button.setVisible(False)
        #     self.export_button.setVisible(False)
        #
        #     # Reveal done button
        #     self.close_button.setVisible(True)
        #
        #     # Make progress bar green (to indicate we are done)
        #     # from PyQt5.QtGui import QPalette
        #     # p = QPalette()
        #     # p.setColor(QPalette.Highlight, Qt.green)
        #     # self.progressExportVideo.setPalette(p)
        #
        #     # Raise the window
        #     self.show()
        # else:
        #     # Accept dialog
        #     super(SuperResolution, self).accept()

        success_hint = QDialog()
        success_hint.setWindowTitle("成功")
        success_hint.exec_()

    def cancel(self):
        log.info("Exit the dialog of super resolution. ")
        super(SuperResolution, self).reject()


