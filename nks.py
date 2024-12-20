#!/usr/bin/env python

def getInd(fileHandle, address, xor=False):
    fileHandle.seek(address)
    if xor == True:
            #print("xor == True in getInd")
            bxor = int.from_bytes(fileHandle.read(1), byteorder='little')
    address = int.from_bytes(fileHandle.read(4), byteorder='little')
    if xor == True:
        address ^= bxor
    return address
def getStr(fileHandle, address, xor=True, maxlength=20000):
    fileHandle.seek(address)
    if xor == True:
            #print("xor == True in getStr")
            bxor = int.from_bytes(fileHandle.read(1), byteorder='little')
    length = int.from_bytes(fileHandle.read(4), byteorder='little')
    if xor == True:
        length ^= bxor
    if length > maxlength or length == 0:
#        raise Exception(f"Length is {length}!")
         return None, None
    string = fileHandle.read(length)
    decoded = bytearray()
    for char in string:
        decoded.append(char^bxor)
    try:
        decoded = decoded.decode('utf8')
    except UnicodeDecodeError:
        decoded = decoded.decode('cp1251')
    except:
        return None, None
    if decoded[:6] != "<BODY>":
        return None, None
    return length, decoded
