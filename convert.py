#!/usr/bin/env python
from bs4 import BeautifulSoup
from tqdm import tqdm
import re
import nks
from rsanu2 import rsanu2, sup
import slob

# The searchable index lives in the slot table that the header points to:
#   offset 108 -> table start (word pointers), offset 112 -> table end
# (offset 100 is the raw HTML-data region, not the index -- a common misread.)
IND = 108
STRIDE = 10  # per slot: [xor][word_ptr][xor][record_ptr]

nksFile = open("Docum.nks", "rb")
begin = nks.getInd(nksFile, IND)          # raw header int (offset 108, xor=False)
end   = nks.getInd(nksFile, IND + 4)      # raw header int (offset 112)
count = (end - begin) // STRIDE

w = slob.create("srpski.slob")

with tqdm(total=end - begin, unit_scale=True, unit="B") as pbar:
	for i in range(count):
		slot = begin + i * STRIDE
		word_ptr   = nks.getInd(nksFile, slot, xor=True)
		record_ptr = nks.getInd(nksFile, slot + 5, xor=True)
		length, body = nks.getStr(nksFile, record_ptr)  # cp1251, must be <BODY>
		length, headword = nks.getStr(nksFile, word_ptr,
									encoding='utf-16-le',
									require_body=False)  # UTF-16 headword
		if body is None or headword is None:
			continue
		soup = BeautifulSoup(body, 'html.parser')
		try:
			for tag in soup.find_all('span'):
				if tag.string and "RSANU2" in (tag.get('style') or ''):
					tag.string = tag.string.translate(rsanu2)
				if tag.has_attr('class') and tag['class'] == 'style3':
					tag.name = 'b'
				if tag.has_attr('lang') and tag['lang'] == 'SR-CYR':
					tag['lang'] = 'sr'
			for tag in soup.find_all('sup', recursive=True, string=True):
				if tag.string:
					tag.string = tag.string.translate(sup)
			w.add(soup.encode("utf-8"), headword, content_type=slob.MIME_HTML)
		except AttributeError as e:
			print(i, headword, ":", "NONETYPE", e)
		pbar.update(STRIDE)

w.finalize()
nksFile.close()
