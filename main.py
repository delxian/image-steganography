"""todo"""
#pylint: disable=invalid-name
from collections import deque
from collections.abc import Iterator
from functools import cache
from itertools import chain
import math
import os
import string
from tkinter.filedialog import askopenfilename, asksaveasfilename

from PIL import Image


END_OF_TEXT = "00000011"  # https://www.ascii-code.com/character/%E2%90%83

# images downloaded at medium size and converted to .png in paint
# https://www.pexels.com/photo/photo-of-buildings-during-nighttime-2603464/  buildings.png
# https://www.pexels.com/photo/multicolored-abstract-painting-2860810/  abstract.png
# https://www.pexels.com/photo/colorful-lanterns-hanging-4406455/  lanterns.png
# https://www.pexels.com/photo/white-clouds-and-blue-sky-3689875/  umbrella.png
# https://www.pexels.com/photo/stairs-grayscale-photography-921025/  stairs.png


def str_to_bin(text: str) -> str:
    """Convert an ASCII (8-bit) string to a binary string."""
    return ''.join([bin(ord(i))[2:].zfill(8) for i in text])

def bin_to_str(bits: str) -> str:
    """Convert a binary string to an ASCII (8-bit) string."""
    bits = bits[: len(bits) - len(bits) % 8]  # truncate incomplete bytes from end
    partitioned = [bits[i*8 : i*8 + 8] for i in range(int(len(bits)/8))]
    return ''.join([chr(int(i, 2)) for i in partitioned])

def cycle_cipher(text: str, code: str, decode: bool = False) -> str:
    """Encipher/decipher a string with a sequence of rotations of every n characters."""
    @cache
    def alpha_to_cycle(text: str) -> str:
        """Convert letters to codes for the cycle cipher."""
        def digital_root(n: int) -> int:
            """Get the ultimate 1-digit sum of a number's digits."""
            while n // 10:
                n = sum(int(x) for x in str(n))
            return n

        if len(text) > 1:
            return ''.join(alpha_to_cycle(x) for x in text)
        if (text := text.lower()) not in string.ascii_lowercase:
            return ''  # non-letter characters do nothing

        # methods for calculating interval/offset/shift are mostly arbitrary
        # main idea was getting interval/shift relatively low and offset < interval
        value = ord(text) - 96  # a >> 1, z >> 26
        interval = int(value)
        while True:
            # get largest factor from 2, 3, 4, 5
            if (factor := next((n for n in range(5, 1, -1) if not interval % n), 0)):
                interval = factor
                break
            # if not possible, get digital root in 2, 3, 4, 5
            if (root := digital_root(interval)) in range(2, 6):
                interval = root
                break
            # if not possible, incrememnt value and start over
            interval += 1

        # offset is always < interval and most of the time 0 or 1
        offset = digital_root(value * digital_root(value)) % interval
        shift = value % 5 + 1
        return ''.join(str(n) for n in (interval, offset, shift))

    new_text = [*text]
    if not code.isnumeric():
        code = alpha_to_cycle(code)
    if len(code) % 3:
        raise ValueError("Numerical code length must be a multiple of 3")
    if not all(int(n) for n in code[::3]):
        raise ValueError("Intervals must be non-zero")
    group_count = len(code) // 3
    for n in range(group_count):
        if decode:
            n = group_count - (n+1)  # reverse group order
        interval, offset, shift = [int(x) for x in code[n*3 : n*3 + 3]]
        chars = deque(new_text[offset :: interval])
        chars.rotate(shift if decode else -shift)
        for i, char in enumerate(chars):
            new_text[offset + i*interval] = char
    return ''.join(new_text)

def closest_coprimes(dividend: int, num: int) -> tuple[int, int]:
    """Get the coprimes of a number closest below and above a starting value."""
    lower, higher = num, num
    while True:
        higher += 1
        if math.gcd(higher, dividend) == 1:
            break
    while True:
        lower -= 1
        if math.gcd(lower, dividend) == 1:
            break
    return (lower, higher)


class SteganoImage:
    """Implement image steganography with 24-bit color."""

    def __init__(self, image: Image.Image):
        self.image = image
        raw_image_data = self.image.getdata()
        if len(raw_image_data[0]) == 4:
            self.image = self.image.convert('RGB')  # omit transparency data
            raw_image_data = self.image.getdata()
        self.image_data = list(chain.from_iterable(raw_image_data))  # collapse to 1D array
        self.pixel_length = len(raw_image_data)  # pixels in image
        self.color_length = len(self.image_data)  # color values in image (pixels * 3)
        assert self.pixel_length*3 == self.color_length, "Image is not 3 colors per pixel"

    def encode(self, text: str, interval: int = 0,
               offset: int = 0) -> tuple[Image.Image, int, int]:
        """Encode text into an image."""
        image = self.image.copy()
        image_data = list(chain.from_iterable(image.getdata()))
        text_binary = str_to_bin(text) + END_OF_TEXT  # end of text character
        if len(text_binary) > self.color_length:
            raise ValueError("Text too long for carrier image")
        interval = interval if interval else self.color_length // len(text_binary)
        indices = SteganoImage.distribute(
            len(text_binary), self.color_length, interval, offset)
        for bit, index in zip(text_binary, indices):
            color = image_data[index]
            image_data[index] = self.modify_color(color, int(bit), "LSB")
            pixel_index = index // 3
            y, x = divmod(pixel_index, image.width)
            rgb = tuple(image_data[pixel_index*3 : pixel_index*3+3])
            image.putpixel((x, y), rgb)  # type: ignore
        return (image, interval, offset)

    @staticmethod
    def modify_color(color: int, data: int, mode: str) -> int:
        """Modify the value of a single color in an image to encode data."""
        if mode == "LSB":  # 1 data bit to 1 color bit
            if color not in range(256):
                raise ValueError("Invalid 8-bit color value")
            if data.bit_length() > 1:
                raise ValueError("Too much data bits for LSB mode")
            return (color & ~1) + data
        return color

    @staticmethod
    def decode(image: Image.Image, interval: int, offset: int = 0) -> str:
        """Extract text from a pre-encoded image."""
        image = image.convert('RGB')  # omit transparency data
        image_data = list(chain.from_iterable(image.getdata()))
        indices = SteganoImage.distribute(
            len(image_data), len(image_data), interval, offset)
        reconstructed_binary: str = ''
        for index in indices:
            reconstructed_binary += str(image_data[index] % 2)
            if not len(reconstructed_binary) % 8:
                # stop reading at end of text character
                if reconstructed_binary[-8:] == END_OF_TEXT:
                    break
        return bin_to_str(reconstructed_binary)

    @staticmethod
    def distribute(data_length: int, carrier_length: int,
                   interval: int = 0, offset: int = 0) -> Iterator[int]:
        """
        Generate a semi-even distribution of indices across a range. \\
        Supports looping behavior where indices beyond the carrier length \\
        loop back to the start with no overlap, even in the worst case scenario. \\
        For this to occur, the interval must be coprime with the carrier length.
        """
        if data_length > carrier_length:
            raise ValueError("Insufficient space")
        interval = interval if interval else carrier_length // data_length
        if math.gcd(interval, carrier_length) != 1:  # coprimes guarantee no overlap
            interval = closest_coprimes(carrier_length, interval)[1]
        if interval > carrier_length:
            raise RuntimeError("Interval too high")  # technically not a problem
        offset %= interval
        return ((n*interval + offset) % carrier_length for n in range(data_length))


image_filepath = askopenfilename(
    title="Select image", filetypes=[("Image files", "*.png")])
my_image = Image.open(image_filepath)
print(f"Loaded image {os.path.basename(image_filepath)}.")
print(f"Image dimensions: {my_image.size}")
if (encode := input("Encode or decode message? (e/d): ")) == 'e':
    stegano_image = SteganoImage(my_image)
    print(f"Maximum LSB encoding: {stegano_image.color_length} bits, " \
          f"{stegano_image.color_length // 8} characters")
    if not (encode_text := input("Enter text to encode (leave blank to choose .txt file): ")):
        text_filepath = askopenfilename(
            title="Select text file", filetypes=[("Text files", "*.txt")])
        with open(text_filepath, mode='r', encoding="UTF-8") as file:
            encode_text = file.read()
        encode_text = ''.join(filter(lambda x: x in string.printable, encode_text))
        print(f"Loaded text {os.path.basename(text_filepath)}.")
    print(f"Text length: {len(encode_text)} characters")
    if input("Encipher text using cycle cipher? (y/n): ") == 'y':
        print("Rotation parameters follow an IOS format - Interval, Offset, Shift")
        cipher_code = input("Enter code for cycle cipher " \
                            "(letters or groups of 3 numbers [e.g. apple, 314202]): ")
        encode_text = cycle_cipher(encode_text, cipher_code)
    if input("Show text to encode? (y/n): ") == 'y':
        print(f"Text to encode: {encode_text}")
    encoding_interval = input(
        "Enter custom distribution interval (leave blank for even distribution): ")
    encoding_interval = int(encoding_interval) if encoding_interval else 0
    encoding_offset = input("Enter custom distribution offset (leave blank for 0): ")
    encoding_offset = int(encoding_offset) if encoding_offset else 0
    encoded, encoding_interval, encoding_offset = stegano_image.encode(
        encode_text, interval=encoding_interval, offset=encoding_offset)
    if input("Save encoded image? (y/n): ") == 'y':
        output_image_filepath = asksaveasfilename(
            title="Save image", filetypes=[("Image files", "*.png")])
        encoded = encoded.convert("RGB")
        encoded.save(output_image_filepath, format="PNG", quality=100)
        print(f"Image saved to {output_image_filepath}.")
        print(f"Encoding interval: {encoding_interval}")
        print(f"Encoding offset: {encoding_offset}")
        print("Remember these values; you cannot decode the text without them.")
else:
    decoding_interval = int(input("Enter interval for decoding: "))
    decoding_offset = int(input("Enter offset for decoding: "))
    decoded_text = SteganoImage.decode(my_image, decoding_interval, decoding_offset)
    if input("Decipher text using cycle cipher? (y/n): ") == 'y':
        cipher_code = input("Enter code for cycle cipher " \
                            "(string or groups of 3 numbers [e.g. apple, 314202]): ")
        decoded_text = cycle_cipher(decoded_text, cipher_code, decode=True)
    if input("Show decoded text? (y/n): ") == 'y':
        print(f"Decoded text: {decoded_text}")
    print(f"Text length: {len(decoded_text)} characters")
    if input("Save decoded text to .txt? (y/n): ") == 'y':
        output_text_filepath = asksaveasfilename(
            title="Save text", filetypes=[("Text files", "*.txt")])
        with open(output_text_filepath, mode='w', encoding="UTF-8") as file:
            file.write(decoded_text)
        print(f"Text saved to {output_text_filepath}.")
