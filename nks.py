#!/usr/bin/env python

import numpy

def getInd(fileHandle, address, xor=False):
    fileHandle.seek(address)
    if xor == True:
            bxor = int.from_bytes(fileHandle.read(1), byteorder='little')
    address = int.from_bytes(fileHandle.read(4), byteorder='little')
    if xor == True:
        address ^= bxor
    return address
def getStr(fileHandle, address, xor=True, maxlength=20000):
    fileHandle.seek(address)
    if xor == True:
            bxor = fileHandle.read(1)
    length = int.from_bytes(fileHandle.read(4), byteorder='little')
    if xor == True:
        length ^= int.from_bytes(bxor, byteorder='little')
    if length > maxlength or length == 0:
         return None, None
    string = fileHandle.read(length)
    decoded = (numpy.frombuffer(bxor,dtype=numpy.uint8)^numpy.frombuffer(string, dtype=numpy.uint8)).tobytes()
    try:
        decoded = decoded.decode('utf8')
    except UnicodeDecodeError:
        decoded = decoded.decode('cp1251')
    except:
        return None, None
    if decoded[:6] != "<BODY>":
        return None, None
    return length, decoded
