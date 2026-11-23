#!/usr/bin/env python

import numpy

def getInd(fileHandle, address, xor=False):
    # xor=False -> raw header int (no xor byte, e.g. table begin/end at 108/112)
    # xor=True  -> pointer from a slot ([xor byte][int32]) read with mask = 1
    fileHandle.seek(address)
    if xor == True:
            bxor = int.from_bytes(fileHandle.read(1), byteorder='little')
    address = int.from_bytes(fileHandle.read(4), byteorder='little')
    if xor == True:
        address ^= bxor
    return address
def getStr(fileHandle, address, xor=True, encoding=None, require_body=True):
    # encoding=None -> try utf-8 then fall back to cp1251 (original behavior)
    # require_body=False -> do not reject non-<HTML> data (used for UTF-16 headwords)
    fileHandle.seek(address)
    if xor == True:
            bxor = fileHandle.read(1)
    length = int.from_bytes(fileHandle.read(4), byteorder='little')
    if xor == True:
        length ^= int.from_bytes(bxor, byteorder='little')
    if length == 0:
         return None, None
    string = fileHandle.read(length)
    decoded = (numpy.frombuffer(bxor,dtype=numpy.uint8)^numpy.frombuffer(string, dtype=numpy.uint8)).tobytes()
    if encoding is None:
        try:
            decoded = decoded.decode('utf8')
        except UnicodeDecodeError:
            decoded = decoded.decode('cp1251')
    else:
        decoded = decoded.decode(encoding)
    if require_body and decoded[:6] != "<BODY>":
        return None, None
    return length, decoded
