#!/usr/bin/env python
from bs4 import BeautifulSoup
from tqdm import tqdm
import nks
import rsanu2
import slob

mimetypes = {
		".html":"text/html; charset=utf-8",
		".css": "text/css; charset=utf-8",
		".jpg": "image/jpg"
	}

nksFile = open("Docum.nks", "rb")
nksData = {}

for index in [100]: #, 124
	nksData[index] = {}
	addr = nks.getInd(nksFile, index)
	with tqdm(initial=nks.getInd(nksFile, index), total=nks.getInd(nksFile, index+8)) as pbar:
		while addr < nks.getInd(nksFile, index+8):
			try:
				length, output = nks.getStr(nksFile, addr)
				if output is not None:
					nksData[index][addr] = {'content': output, 'length': length}
					addr += length
					pbar.update(length)
				else:
					addr += 1
			except UnicodeDecodeError:
				addr += 1

w = slob.create("srpski.slob")

for word in nksData[100]:
	soup = BeautifulSoup(nksData[100][word]['content'], 'html.parser')
	try:
		headWord = ""
		b = soup.find('b')
		while b.name == 'b':
			headWord += b.get_text()
			if b.find_next_sibling() is not None:
				b = b.find_next_sibling()
			else:
				 break
		headWord = rsanu2.rsanudecode.sub(lambda x: rsanu2.rsanu[x.group()], headWord)
		headWord = headWord.rstrip(', ')
		for tag in soup.findAll('span', string=True):
			tag.string = rsanu2.rsanudecode.sub(lambda x: rsanu2.rsanu[x.group()], tag.string)
		print(word, ":", headWord)
		w.add(soup.encode("utf-8"), headWord, content_type=mimetypes[".html"])
	except AttributeError:
		print(word, ":", "NONETYPE")
w.finalize()
