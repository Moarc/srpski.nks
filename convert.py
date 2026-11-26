#!/usr/bin/env python
from tqdm import tqdm
import nks
from rsanu2 import rsanu2
import slob
from selectolax.lexbor import LexborHTMLParser

# The searchable index lives in the slot table that the header points to:
#   offset 108 -> table start (word pointers), offset 112 -> table end
# (offset 100 is the raw HTML-data region, not the index -- a common misread.)
IND = 108
STRIDE = 10  # per slot: [xor][word_ptr][xor][record_ptr]


def transform(body):
	"""Convert a <BODY> record to a bare <p>… slob blob (selectolax).

	Tag unwrap (tag dropped, text kept):
	  <a href=_msoanchor_N> (Word track-change bookmark links),
	  <h1> (section markers).
	Tag rename:
	  class="style1" -> <sup>, class="style2" -> <i>, class="style3" -> <b>
	  mso-bidi-font-style:italic -> <i>, mso-bidi-font-weight:bold -> <b>
	Lang:
	  lang= and mso-ansi-language both normalized to ISO-639-1 lang= (SR-CYR/SR
	  -> sr, RU -> ru, HR -> hr, TR -> tr, EL -> el, BG -> bg, EN-US -> en).
	Stripped presentation:
	  class (all Mso* / fr* / MsoBodyText* / etc.), FONT-SIZE, MARGIN-RIGHT,
	  FONT-FAMILY {rsanu2, Times New Roman, OliveraRas, TNRa01, Arial Narrow},
	  mso-ansi-language, plus margin/layout-grid-mode/text-align/text-indent/
	  mso-bidi-font-size/letter-spacing/mso-bookmark/mso-prop-change/
	  margin-left/font-style/mso-bidi-font-style/mso-bidi-font-weight.
	  color, text-transform:uppercase, and the Symbol glyph face are kept.
	Content:
	  RSANU2 spans translate ALL child text (nested tags preserved).
	  Wingdings '?' -> <sup>+</sup>.
	  <sup>0</sup>/<sup>°</sup> -> ° (tag dropped); other <sup> left as-is.
	  <sup>l</sup> -> <sup>1</sup> (lumped sub-entry marker 'l' is really '1');
	    only a lone 'l' text node whose parent is <sup> is rewritten.
	  <sub>/<u> left as-is (no translation).
	"""
	p = LexborHTMLParser(body, is_fragment=True)   # is_fragment drops <html><head><body>
	root = p.root
	if root is None:
		return None

	def norm_lang(v):
		# SR-CYR -> sr, EN-US -> en, RU -> ru, ...
		return v.strip().lower().split('-')[0]

	# 0) One pre-order pass over elements AND text nodes that folds the four
	#    pre-class-rename steps together (previously 4 separate traversals):
	#      - unwrap structural tags (drop the tag, keep text/descendants):
	#        <a href=_msoanchor_N> (Word track-change bookmarks) and <h1> (markers);
	#      - Wingdings '?' -> split into pieces with a '+' per '?' inside a
	#        <sup> (the only Wingdings glyph; font-family stripped in phase 3,
	#        so detect the marker here); Symbol-font glyphs are handled elsewhere;
	#      - <sup>0</sup>/<sup>°</sup> -> drop the tag, keep '°' (degree sign);
	#      - lone <sup>l</sup> -> keep tag, rewrite 'l' to '1' (corrupted marker).
	#    Markers are disjoint and unwrapping a/h1 only reparents, so the order
	#    within this single pass matches the old separate passes.  Run before
	#    phase 1 creates new <sup> from class=style1, so those are untouched.
	for node in list(root.traverse(include_text=True)):
		if node.is_text_node:
			t = node.text()
			if '?' in t:
				par = node.parent
				while par is not None:
					if 'wingdings' in (par.attributes.get('style') or '').lower():
						break
					par = par.parent
				if par is not None:
					pieces = t.split('?')
					for i, piece in enumerate(pieces):
						if piece:
							node.insert_before(piece)
						if i < len(pieces) - 1:
							s = p.create_node('sup')
							s.insert_child('+')
							node.insert_before(s)
					node.replace_with('')
			elif t == 'l' and node.parent is not None and node.parent.tag == 'sup':
				node.replace_with('1')
		elif node.tag in ('a', 'h1'):
			node.unwrap()
		elif node.tag == 'sup' and node.text() in ('0', '\u00b0'):
			node.replace_with('\u00b0')

	# 1) class-based tag rename (style1 -> sup, style2 -> i, style3 -> b).
	#    Rebuild the node (tags are immutable in selectolax); class is dropped,
	#    lang copied through norm_lang; other attrs (incl. style) carried over.
	for sp in list(root.css('span')):
		parts = (sp.attributes.get('class') or '').split()
		if not parts:
			continue
		if 'style3' in parts:
			tag, b = 'b', p.create_node('b')
		elif 'style2' in parts:
			tag, b = 'i', p.create_node('i')
		elif 'style1' in parts:
			tag, b = 'sup', p.create_node('sup')
		else:
			continue
		for k, v in sp.attrs.items():
			if k == 'class':
				continue
			if k == 'lang':
				b.attrs['lang'] = norm_lang(v)
			else:
				b.attrs[k] = v
		# Move ALL direct children in document order (elements as whole subtrees,
		# then interleaved text).  A two-step move (elements first, text second)
		# would reorder: any <sup>/<sub> that appears AFTER running text inside the
		# span would jump to the front.  el.iter(include_text=True) yields
		# direct children in source order.
		for c in list(sp.iter(include_text=True)):
			b.insert_child(c, move=True)
		sp.replace_with(b)
	# 2) RSANU2: translate all child text within RSANU2 spans.
	#    MUST run before phase 3 strips FONT-FAMILY:rsanu2 (else the
	#    RSANU2 style marker vanishes and these nodes go untranslated).
	to_translate = []
	for node in root.traverse(include_text=True):
		if node.is_text_node and node.text():
			par = node.parent
			while par is not None:
				if 'RSANU2' in (par.attributes.get('style') or ''):
					to_translate.append(node)
					break
				par = par.parent
	for node in to_translate:
		node.replace_with(node.text().translate(rsanu2))
	# 3) normalize lang (lang= and mso-ansi-language -> lang=), strip MsoNormal
	#    class and presentation declarations, drop now-empty style attrs.
	#    Collect mso-bidi-font-style:italic / mso-bidi-font-weight:bold nodes
	#    for the tag-rebuild pass in phase 4.  Stripped font-family values are
	#    rsanu2 and other alternate/glyph faces (Times New Roman, OliveraRas,
	#    TNRa01, Arial Narrow); the Symbol glyph face is kept.
	STRIP_PROPS = {
		'margin', 'layout-grid-mode', 'text-align', 'text-indent',
		'mso-bidi-font-size', 'letter-spacing', 'mso-bookmark',
		'mso-prop-change', 'margin-left', 'font-style',
		'mso-bidi-font-style', 'mso-bidi-font-weight', 'font-weight',
	}
	STRIP_FONTS = {'rsanu2', 'times new roman', 'oliveraras', 'tnra01', 'arial narrow', 'wingdings'}
	to_rebuild = []
	for el in list(root.traverse()):
		if 'class' in el.attrs:
			del el.attrs['class']
		lang_val = None
		if 'lang' in el.attributes:
			lang_val = norm_lang(el.attributes['lang'])
			el.attrs['lang'] = lang_val
		style = el.attributes.get('style')
		if not style:
			continue
		kept = []
		has_mso = False
		mso_val = None
		make_i = False
		make_b = False
		for decl in style.split(';'):
			decl = decl.strip()
			if not decl or ':' not in decl:
				continue
			prop, val = decl.split(':', 1)
			prop_p = prop.strip().lower()
			val_l = val.strip().lower()
			if prop_p == 'mso-ansi-language':
				has_mso = True
				mso_val = norm_lang(val)
				continue
			if prop_p in ('font-size', 'margin-right'):
				continue
			if prop_p == 'font-family':
				if val_l not in ('symbol',) and val_l in STRIP_FONTS:
					continue
				kept.append(decl)
				continue
			if prop_p == 'mso-bidi-font-style' and val_l == 'italic':
				make_i = True
				continue
			if prop_p == 'mso-bidi-font-weight' and val_l == 'bold':
				make_b = True
				continue
			if prop_p == 'font-weight' and val_l == 'bold':
				make_b = True
				continue
			if prop_p in STRIP_PROPS:
				continue
			kept.append(decl)
		if has_mso and (lang_val is None or 'lang' not in el.attributes):
			lang_val = mso_val
			el.attrs['lang'] = lang_val
		if make_i:
			to_rebuild.append((el, 'i'))
		if make_b:
			to_rebuild.append((el, 'b'))
		if kept:
			el.attrs['style'] = '; '.join(kept)
		else:
			del el.attrs['style']

	# 4) rebuild collected italic/bold nodes to <i>/<b> (tags are immutable in
	#    selectolax; rebuild, dropping class, carrying lang and other attrs).
	for el, tag in to_rebuild:
		if el.tag == tag:
			continue
		b = p.create_node(tag)
		for k, v in el.attrs.items():
			if k == 'class':
				continue
			if k == 'lang':
				b.attrs['lang'] = norm_lang(v)
			else:
				b.attrs[k] = v
		# Move ALL direct children in document order (elements as whole subtrees,
		# then interleaved text) so a <sup>/<sub> inside the italic/bold span
		# keeps its original position instead of jumping to the front.
		for c in list(el.iter(include_text=True)):
			b.insert_child(c, move=True)
		el.replace_with(b)
	return p.html


nksFile = open("Docum.nks", "rb")
begin = nks.getInd(nksFile, IND)          # raw header int (offset 108, xor=False)
end   = nks.getInd(nksFile, IND + 4)      # raw header int (offset 112)
count = (end - begin) // STRIDE

w = slob.create("srpski.slob")
w.tag("label", "Српски електронски речник")

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
		headword = headword.replace('\u006c', '')  # drop stray Latin 'l' from headword
		try:
			html = transform(body)
		except Exception as e:
			print(i, headword, ":", type(e).__name__, e)
			continue
		if html is None:
			continue
		w.add(html.encode("utf-8"), headword, content_type=slob.MIME_HTML)
		pbar.update(STRIDE)

w.finalize()
nksFile.close()
