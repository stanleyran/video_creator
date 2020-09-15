import streamlit as st
import altair as alt
import pandas as pd
import numpy as np
import os
import urllib
import cv2
import uuid

# optique required lib
from glob import glob
import grpc
import json
import logging
from PIL import Image, ImageDraw, ImageFont


"""
How to try out
1. pip --no-cache-dir install --upgrade streamlit opencv-python
2. pip --no-cache-dir install mmcv-full==latest+torch1.6.0+cu101 -f https://openmmlab.oss-accelerate.aliyuncs.com/mmcv/dist/index.html
3. streamlit run --server.port 8080 --server.enableCORS false app.py
At this point, webapp should pop up in your brower
"""

DATA_PATH = '/export/home/video_gen/data'


def main():
    # Render the readme as markdown using st.markdown.

    # Once we have the dependencies, add a selector for the app mode on the sidebar.
    st.sidebar.title("What to do")
    app_mode = st.sidebar.selectbox("Choose the app mode",
                                    ["Run the app"])

    if app_mode == "Run the app":
        run_the_app()


def run_the_app():
    skus = glob(os.path.join(DATA_PATH, 'images')+'/*')
    sku_path = st.sidebar.selectbox("Pick a product.", skus)
    sku_images = glob(os.path.join(sku_path+'/*'))
    for im_fn in sku_images:
        st.image(im_fn, width=400)

    effects = ['translate', 'zoom_in_hold', 'zoom_out_hold', 'multicrop']
    selected_filter = st.sidebar.selectbox("Pick a effect", effects)

    music_files = glob(os.path.join(DATA_PATH, 'music') + '/*')
    music_path = st.sidebar.selectbox("Pick a background music", music_files)

    st.write('Running video creation')
    out_fn = os.path.join(DATA_PATH, 'videos', os.path.basename(
        sku_images)+'_' + selected_filter + '.mp4')
    vid = gen_video(sku_images, out_fn,
                    filter=selected_filter, music=music_path)

    """
    st.write("Visualizing detection results")
    name = filename.split('.')
    filepath_new = os.path.join(OUTPUT_PATH, '{}_{}.{}'.format(
        name[0], str(uuid.uuid4()), name[-1]))
    os.system("ffmpeg -y -i {} -vcodec libx264 {}".format(filepath, filepath_new))
    """
    with open(vid, 'rb') as f:
        video_final_byte = f.read()
    st.video(video_final_byte)


if __name__ == "__main__":
    main()
