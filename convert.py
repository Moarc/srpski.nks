#!/usr/bin/env python
from bs4 import BeautifulSoup
from tqdm import tqdm
import re
import nks
from rsanu2 import rsanu2, sup
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
	with tqdm(initial=nks.getInd(nksFile, index), total=nks.getInd(nksFile, index+8), unit_scale=True, unit="B") as pbar:
		while addr < nks.getInd(nksFile, index+8):
			try:
				length, output = nks.getStr(nksFile, addr)
				if output is not None:
					nksData[index][addr] = {'content': output, 'length': length}
					addr += length
					pbar.update(length)
				else:
					addr += 1
					pbar.update(1)
			except UnicodeDecodeError:
				addr += 1
				pbar.update(1)

w = slob.create("srpski.slob")

for word in nksData[100]:
	soup = BeautifulSoup(nksData[100][word]['content'], 'html.parser')
	try:
		for tag in soup.find_all('span', string=True):
			if tag.has_attr('style') and "RSANU2" in tag['style']:
				tag.string = tag.string.translate(rsanu2)
			if tag.has_attr('class') and tag['class'] == 'style3':
				tag.name = 'b'
		for tag in soup.find_all('sup', recursive=True, string=True):
			tag.string = tag.string.translate(sup)
		headWord = ""
		b = soup.find('b')
		while b.name == 'b':
			headWord += b.get_text()
			if b.find_next_sibling() is not None:
				b = b.find_next_sibling()
			else:
				 break
		headWord = re.sub(r"(([0-9IV]*\.?)|,.*)", "", headWord)
		headWord = headWord.rstrip()
		print(word, ":", headWord)
		w.add(soup.encode("utf-8"), headWord, content_type=mimetypes[".html"])
	except AttributeError:
		print(word, ":", "NONETYPE")
w.finalize()
