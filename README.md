# Image Steganography
Encodes text within the color data of a PNG image.

## Features
- Image steganography encoding and decoding
- Load text to encode from .txt and/or save decoded text to .txt
- Semi-even data distribution across the image with looping behavior
- Five demo images from [Pexels](https://www.pexels.com/) (medium size, converted from .jpg to .png)
- Three sample texts
    - [Declaration of Independence](https://www.archives.gov/founding-docs/declaration-transcript) - 9KB, ~8.2K characters
    - [Lorem ipsum, 50 paragraphs](https://www.lipsum.com/) - 29KB, ~29.5K characters
    - [Romeo and Juliet](https://www.gutenberg.org/ebooks/1513), from [Project Gutenberg](https://www.gutenberg.org/policy/license.html) - 164KB, ~166.9K characters
        - This eBook is for the use of anyone anywhere in the United States and most other parts of the world at no cost and with almost no restrictions whatsoever. You may copy it, give it away or re-use it under the terms of the Project Gutenberg License included with this eBook or online at www.gutenberg.org. If you are not located in the United States, you will have to check the laws of the country where you are located before using this eBook.
- Custom cycle cipher with letter-to-parameter conversion

## Steganography

[Steganography](https://en.wikipedia.org/wiki/Steganography) is the act of concealing information within other information. This project uses the color values of pixels in a PNG image to encode ASCII text as binary. Once encoded, the text can be extracted from the image given the interval and offset used to encode it. This project currently uses the LSB (least significant bit) encoding method, which modifies only the least significant bit of each color value, resulting in imperceptible changes to the image.

## Data Distribution

Given the encoded binary data is shorter than the number of color values in the image, binary data is distributed semi-evenly across the image. If the distribution interval extends the encoded data beyond the length of the image data, the overflow data loops back to the beginning exhaustively such that no two data bits overlap. This is accomplished using the modulo operator and its behavior with coprimes. If the encoding interval is coprime with the length of the carrier, it guarantees that no two indices of data bits are equal, even in the worst case scenario where the data length is equal to the carrier length.

For example, if both the data and carrier are 20 entries long, as long as the interval is coprime with 20, there will be no identical indices:

```
data_length, carrier_length = 20, 20
indices = list(SteganoImage.distribute(data_length, carrier_length, interval=3))  # coprime
# [0, 3, 6, 9, 12, 15, 18, 1, 4, 7, 10, 13, 16, 19, 2, 5, 8, 11, 14, 17]
len(set(indices)) == 20  # True
indices = list(SteganoImage.distribute(data_length, carrier_length, interval=7))  # coprime
# [0, 7, 14, 1, 8, 15, 2, 9, 16, 3, 10, 17, 4, 11, 18, 5, 12, 19, 6, 13]
len(set(indices)) == 20  # True
indices = list(SteganoImage.distribute(data_length, carrier_length, interval=11))  # coprime
# [0, 11, 2, 13, 4, 15, 6, 17, 8, 19, 10, 1, 12, 3, 14, 5, 16, 7, 18, 9]
len(set(indices)) == 20  # True
indices = list(SteganoImage.distribute(data_length, carrier_length, interval=5))  # not coprime
# [0, 5, 10, 15, 0, 5, 10, 15, 0, 5, 10, 15, 0, 5, 10, 15, 0, 5, 10, 15]
len(set(indices)) == 20  # False
indices = list(SteganoImage.distribute(data_length, carrier_length, interval=6))  # not coprime
# [0, 6, 12, 18, 4, 10, 16, 2, 8, 14, 0, 6, 12, 18, 4, 10, 16, 2, 8, 14]
len(set(indices)) == 20  # False
indices = list(SteganoImage.distribute(data_length, carrier_length, interval=14))  # not coprime
# [0, 14, 8, 2, 16, 10, 4, 18, 12, 6, 0, 14, 8, 2, 16, 10, 4, 18, 12, 6]
len(set(indices)) == 20  # False
```

If two numbers are coprime, their greatest common factor is 1. Thus, the expression `math.gcd(a, b) == 1` can be used to determine if `a` and `b` are coprime.

## Cycle Cipher

This program includes an optional cipher to scramble the data before it is encoded into the image. The cipher employs a basic cycling/rotating method that groups every nth character together and rotates them by some amount. Each rotation operation includes an interval, an offset, and a shift amount.

Demonstration:

```
text, code = "This is a test sentence.", "213"  # interval = 2, offset = 1, shift = 3
# every 2nd character, starting at index 1, rotates left by 3 positions
enciphered = cycle_cipher(text, code)  # "T i  estastnse ce.thnsei"
deciphered = cycle_cipher(enciphered, code, decode=True)  # "This is a test sentence."
```

These rotation operations can be chained together to further scramble the data.

While the cycle cipher takes numerical values as parameters, letters are also allowed. The `alpha_to_cipher` function converts each letter in a string into a group of rotation parameters. For example, the word `hello` becomes `414521413413541`, parsed by the cycle cipher as `414`, `521`, `413`, `413`, and `541`. The conversion implementation is mostly arbitrary, and there is no requirement for each letter to have a unique group of parameters.

## Requirements
- Python 3.11 or higher
- [Pillow](https://pypi.org/project/Pillow/)
## License
- [MIT](LICENSE)