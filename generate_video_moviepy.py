#!/usr/bin/env python
from __future__ import unicode_literals, print_function
import argparse
import ffmpeg
import logging
import sys
import os
import csv
import shutil
from moviepy.editor import *
import json
import random
from PIL import Image
import pdb

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)

parser = argparse.ArgumentParser(
    description='Convert speech audio to text using Google Speech API')
parser.add_argument('--in_filename', help='Input filename (`-` for stdin)')
parser.add_argument('--out_filename', help='Output filename (`-` for stdin)')

# screensize = (960, 960)


def resize_func(t, duration):
    if t < 1:
        return 1 + 0.05 * t  # Zoom-in.
    elif 1 <= t <= 2:
        return 1 + 0.05 * 1  # Stay.
    else:  # 2 < t
        return 1 + 0.05 * (duration - t)  # Zoom-out.


def zoom_in_hold_func(t, duration, **kwargs):
    hold_timepoint = kwargs['hold_timepoint']
    zoom_in_rate = kwargs['zoom_in_rate']
    assert hold_timepoint <= duration
    if t < hold_timepoint:
        return 1 + zoom_in_rate * t / hold_timepoint  # Zoom-in.
    else:
        return 1 + zoom_in_rate  # Stay.


def zoom_out_hold_func(t, duration, **kwargs):
    hold_timepoint = kwargs['hold_timepoint']
    # need start from zoom-in version, otherwise padding will occur
    zoom_in_rate = kwargs['zoom_in_rate']
    assert hold_timepoint <= duration
    if t < hold_timepoint:
        # Zoom-out.
        return 1 + zoom_in_rate * (hold_timepoint - t) / hold_timepoint
    else:
        return 1  # Stay.


def zoom_imageclip(image_name, duration, zoom_func, **kwargs):
    clip = (
        ImageClip(image_name)
        .resize(lambda t: zoom_func(t, duration, **kwargs))
        .set_position('top', 'center')
        .set_duration(duration)
    )

    return clip


def translate_func(t, duration, **kwargs):
    hs = kwargs['hs']
    ht = kwargs['ht']
    ws = kwargs['ws']
    wt = kwargs['wt']

    input_h = kwargs['input_h']
    output_h = kwargs['output_h']
    input_w = kwargs['input_w']
    output_w = kwargs['output_w']

    # hs < ht down,
    # hs > ht up, both < 0
    assert hs <= 0 and ht <= 0
    assert -hs <= input_h - output_h  # otherwise first frame has padding on the bottom
    assert -ht <= input_h - output_h

    # ws < wt right,
    # ws > wt left, both < 0
    assert ws <= 0 and wt <= 0
    assert -ws <= input_w - output_w  # otherwise first frame has padding on the right
    assert -wt <= input_w - output_w

    if hs == 0 and ht == 0:
        return ws + (wt - ws) * (t / duration), 'center'
    elif ws == 0 and wt == 0:
        return 'center', hs + (ht - hs) * (t / duration)
    else:
        return ws + (wt - ws) * (t / duration), hs + (ht - hs) * (t / duration)


def translate_imageclip(image_name, duration, **kwargs):
    if 'zoom_in_factor' in kwargs:
        zoom_in_factor = kwargs['zoom_in_factor']
        assert zoom_in_factor >= 1

        clip = (
            ImageClip(image_name)
            .resize(zoom_in_factor)
            .set_duration(duration)
        )
    else:
        clip = ImageClip(image_name).set_duration(duration)

    clip = CompositeVideoClip([clip])  # new input_h, input_w

    video_name = '{}_temp.mp4'.format(image_name)
    clip.write_videofile(video_name, fps=60)

    kwargs['input_h'] = clip.h
    kwargs['input_w'] = clip.w

    # clip = VideoFileClip(video_name).set_position(lambda t: ('center', 50+t))
    clip = VideoFileClip(video_name).set_position(
        lambda t: translate_func(t, duration, **kwargs))

    return clip


def multicrop_imageclip(image_name, duration, duration_per_crop, **kwargs):
    num_clip = duration / duration_per_crop
    w, h = kwargs['w'], kwargs['h']
    margin = 0.2
    clip_list = []
    for i in range(int(num_clip)):
        rand_x, rand_y = random.randint(
            1, int(margin*w)), random.randint(1, int(margin*h))
        resize_factor = random.uniform(0.7, 1)
        new_w = (w-rand_x) * resize_factor
        new_h = (h-rand_y) * resize_factor
        clip = (
            ImageClip(image_name)
            .set_duration(duration_per_crop)
        ).crop(x1=rand_x, y1=rand_y, x2=rand_x+new_w, y2=rand_y+new_h).resize(width=w, height=h)

        clip = CompositeVideoClip([clip], size=(w, h))
        clip.write_videofile('{}_{}.mp4'.format(image_name, i), fps=25)
        clip_list.append(ffmpeg.input('{}_{}.mp4'.format(image_name, i)))

    return clip_list


def color_filter():
    pass


def main(in_filename, out_filename):
    clip_list = []

    audio_clip = ffmpeg.input(
        "/Users/ran.xu/Documents/sf_projects/commerce_vid_gen/data/music/happy1.mp3")

    # min 1350 1234
    fps = 25
    end_frm = 0
    total_dur = 0
    template = zoom_in_hold_func
    #effect = 'translate'
    use_ffmpeg = False
    with open(in_filename) as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',')

        for id, row in enumerate(readCSV):
            image_name = row[0]
            im = Image.open(image_name)
            screensize = (im.width, im.height-50)
            duration = int(row[1])
            effect = str(row[2].strip())
            end_frm += duration * fps
            total_dur += duration
            if use_ffmpeg:
                pass
            else:
                if effect == 'translate':
                    clip = translate_imageclip(image_name, duration,
                                               hold_timepoint=3, zoom_in_rate=0.15,
                                               hs=-30, ht=0, ws=0, wt=0,
                                               input_h=im.height, output_h=im.height-30,
                                               input_w=im.width, output_w=im.width,
                                               )
                    # .set_audio(audio_clip)
                    clip = CompositeVideoClip([clip], size=screensize)
                    clip.write_videofile('{}.mp4'.format(image_name), fps=fps)
                    clip_list.append(ffmpeg.input('{}.mp4'.format(image_name)))
                elif effect == 'zoom_in_hold':
                    clip = zoom_imageclip(image_name, duration, zoom_in_hold_func,
                                          hold_timepoint=3, zoom_in_rate=0.15)
                    # .set_audio(audio_clip)
                    clip = CompositeVideoClip([clip], size=screensize)
                    clip.write_videofile('{}.mp4'.format(image_name), fps=fps)
                    clip_list.append(ffmpeg.input('{}.mp4'.format(image_name)))
                elif effect == 'zoom_out_hold':
                    clip = zoom_imageclip(image_name, duration, zoom_out_hold_func,
                                          hold_timepoint=3, zoom_in_rate=0.15)
                    # .set_audio(audio_clip)
                    clip = CompositeVideoClip([clip], size=screensize)
                    clip.write_videofile('{}.mp4'.format(image_name), fps=fps)
                    clip_list.append(ffmpeg.input('{}.mp4'.format(image_name)))
                elif effect == 'multicrop':
                    duration_per_crop = 1
                    clip_list_per_video = multicrop_imageclip(
                        image_name, duration, duration_per_crop, w=screensize[0], h=screensize[1])
                    clip_list += clip_list_per_video
                else:
                    raise NotImplementedError

                """
                if effect == 'translate':
                    clip = translate_imageclip(image_name, duration,
                                               hold_timepoint=3, zoom_in_rate=0.15,
                                               hs=-30, ht=0, ws=0, wt=0,
                                               input_h=im.height, output_h=im.height-30,
                                               input_w=im.width, output_w=im.width,
                                               )
                    # .set_audio(audio_clip)
                    clip = CompositeVideoClip([clip], size=screensize)
                    clip.write_videofile('{}.mp4'.format(image_name), fps=fps)
                    clip_list.append(ffmpeg.input('{}.mp4'.format(image_name)))
                elif effect == 'zoom':
                    clip = zoom_imageclip(image_name, duration, template,
                                          hold_timepoint=3, zoom_in_rate=0.15)
                    # .set_audio(audio_clip)
                    clip = CompositeVideoClip([clip], size=screensize)
                    clip.write_videofile('{}.mp4'.format(image_name), fps=fps)
                    clip_list.append(ffmpeg.input('{}.mp4'.format(image_name)))
                elif effect == 'multicrop':
                    duration_per_crop = 1
                    clip_list_per_video = multicrop_imageclip(
                        image_name, duration, duration_per_crop, w=screensize[0], h=screensize[1])
                    clip_list += clip_list_per_video
                """
    #a1 = audio_clip.audio.filter('atrim', duration=total_dur)
    # ffmpeg.concat(*clip_list).output(a1,
    #                                 out_filename).run(overwrite_output=True)
    ffmpeg.concat(*clip_list).output(out_filename).run(overwrite_output=True)


def gen_video(images, out_filename, effect=None, music=None):
    clip_list = []
    if music:
        audio_clip = ffmpeg.input(music)

    fps = 25
    end_frm = 0
    total_dur = 0
    duration = 3

    for image_name in images:
        image_name = row[0]
        im = Image.open(image_name)
        screensize = (im.width, im.height-50)
        # pdb.set_trace()
        duration = int(row[1])
        end_frm += duration * fps
        total_dur += duration

        if filter == 'translate':
            clip = translate_imageclip(image_name, duration,
                                       hold_timepoint=3, zoom_in_rate=0.15,
                                       hs=-30, ht=0, ws=0, wt=0,
                                       input_h=im.height, output_h=im.height-30,
                                       input_w=im.width, output_w=im.width,
                                       )
            # .set_audio(audio_clip)
            clip = CompositeVideoClip([clip], size=screensize)
            clip.write_videofile('{}.mp4'.format(image_name), fps=fps)
            clip_list.append(ffmpeg.input('{}.mp4'.format(image_name)))
        elif effect == 'zoom_in_hold':
            clip = zoom_imageclip(image_name, duration, zoom_in_hold_func,
                                  hold_timepoint=3, zoom_in_rate=0.15)
            # .set_audio(audio_clip)
            clip = CompositeVideoClip([clip], size=screensize)
            clip.write_videofile('{}.mp4'.format(image_name), fps=fps)
            clip_list.append(ffmpeg.input('{}.mp4'.format(image_name)))
        elif effect == 'zoom_out_hold':
            clip = zoom_imageclip(image_name, duration, zoom_out_hold_func,
                                  hold_timepoint=3, zoom_in_rate=0.15)
            # .set_audio(audio_clip)
            clip = CompositeVideoClip([clip], size=screensize)
            clip.write_videofile('{}.mp4'.format(image_name), fps=fps)
            clip_list.append(ffmpeg.input('{}.mp4'.format(image_name)))
        elif effect == 'multicrop':
            duration_per_crop = 1
            clip_list_per_video = multicrop_imageclip(
                image_name, duration, duration_per_crop, w=screensize[0], h=screensize[1])
            clip_list += clip_list_per_video
        else:
            raise NotImplementedError
    if music:
        a1 = audio_clip.audio.filter('atrim', duration=total_dur)
        ffmpeg.concat(*clip_list).output(a1,
                                         out_filename).run(overwrite_output=True)
    else:
        ffmpeg.concat(
            *clip_list).output(out_filename).run(overwrite_output=True)


if __name__ == '__main__':
    args = parser.parse_args()
    main(args.in_filename, args.out_filename)
