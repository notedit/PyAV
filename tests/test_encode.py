from __future__ import division

import math

from .common import *

from av.video.stream import VideoStream
from av.audio.stream import AudioStream


WIDTH = 320
HEIGHT = 240
DURATION = 48

def write_rgb_rotate(output):

    if not Image:
        raise SkipTest()

    output.metadata['title'] = 'container'
    output.metadata['key'] = 'value'

    stream = output.add_stream("mpeg4", 24)
    stream.width = WIDTH
    stream.height = HEIGHT
    stream.pix_fmt = "yuv420p"

    for frame_i in range(DURATION):

        frame = VideoFrame(WIDTH, HEIGHT, 'rgb24')
        image = Image.new('RGB', (WIDTH, HEIGHT), (
            int(255 * (0.5 + 0.5 * math.sin(frame_i / DURATION * 2 * math.pi))),
            int(255 * (0.5 + 0.5 * math.sin(frame_i / DURATION * 2 * math.pi + 2 / 3 * math.pi))),
            int(255 * (0.5 + 0.5 * math.sin(frame_i / DURATION * 2 * math.pi + 4 / 3 * math.pi))),
        ))
        frame.planes[0].update_from_string(image.tobytes())

        for packet in stream.encode(frame):
            output.mux(packet)

    for packet in stream.encode(None):
        output.mux(packet)

    # Done!
    output.close()


def assert_rgb_rotate(self, input_):


    # Now inspect it a little.
    self.assertEqual(len(input_.streams), 1)
    self.assertEqual(input_.metadata.get('title'), 'container', input_.metadata)
    self.assertEqual(input_.metadata.get('key'), None)
    stream = input_.streams[0]
    self.assertIsInstance(stream, VideoStream)
    self.assertEqual(stream.type, 'video')
    self.assertEqual(stream.name, 'mpeg4')
    self.assertEqual(stream.average_rate, 24) # Only because we constructed is precisely.
    self.assertEqual(stream.rate, Fraction(24, 1))
    self.assertEqual(stream.time_base * stream.duration, 2)
    self.assertEqual(stream.format.name, 'yuv420p')
    self.assertEqual(stream.format.width, WIDTH)
    self.assertEqual(stream.format.height, HEIGHT)


class TestBasicVideoEncoding(TestCase):

    def test_rgb_rotate(self):

        path = self.sandboxed('rgb_rotate.mov')
        output = av.open(path, 'w')

        write_rgb_rotate(output)
        assert_rgb_rotate(self, av.open(path))


class TestBasicAudioEncoding(TestCase):

    def test_audio_transcode(self):

        path = self.sandboxed('audio_transcode.mov')
        output = av.open(path, 'w')
        output.metadata['title'] = 'container'
        output.metadata['key'] = 'value'

        sample_rate = 48000
        channel_layout = 'stereo'
        channels = 2
        sample_fmt = 's16'

        stream = output.add_stream('mp2', sample_rate)

        ctx = stream.codec_context
        ctx.time_base = sample_rate
        ctx.sample_rate = sample_rate
        ctx.format = sample_fmt
        ctx.channels = channels

        src = av.open(fate_suite('audio-reference/chorusnoise_2ch_44kHz_s16.wav'))
        for frame in src.decode(audio=0):
            frame.pts = None
            for packet in stream.encode(frame):
                output.mux(packet)

        for packet in stream.encode(None):
            output.mux(packet)

        output.close()

        container = av.open(path)
        self.assertEqual(len(container.streams), 1)
        self.assertEqual(container.metadata.get('title'), 'container', container.metadata)
        self.assertEqual(container.metadata.get('key'), None)

        stream = container.streams[0]
        self.assertIsInstance(stream, AudioStream)
        self.assertEqual(stream.codec_context.sample_rate, sample_rate)
        self.assertEqual(stream.codec_context.format.name, 's16p')
        self.assertEqual(stream.codec_context.channels, channels)


class TestEncodeStreamSemantics(TestCase):

    def test_stream_index(self):

        output = av.open(self.sandboxed('output.mov'), 'w')

        vstream = output.add_stream('mpeg4', 24)
        vstream.pix_fmt = 'yuv420p'
        vstream.width = 320
        vstream.height = 240

        astream = output.add_stream('mp2', 48000)
        astream.channels = 2
        astream.format = 's16'

        self.assertEqual(vstream.index, 0)
        self.assertEqual(astream.index, 1)

        vframe = VideoFrame(320, 240, 'yuv420p')
        vpacket = vstream.encode(vframe)[0]

        self.assertIs(vpacket.stream, vstream)
        self.assertEqual(vpacket.stream_index, 0)

        for i in range(10):
            aframe = AudioFrame('s16', 'stereo', samples=astream.frame_size)
            aframe.rate = 48000
            apackets = astream.encode(aframe)
            if apackets:
                apacket = apackets[0]
                break

        self.assertIs(apacket.stream, astream)
        self.assertEqual(apacket.stream_index, 1)
