## Why?
Srpski elektronski rečnik, published in the 2000s, is, AFAIU, the only ever digital publication of data from the Matica srpska and SANU dictionaries. Despite lagging several volumes (by now) behind the publication of the SANU dictionary, it is still the largest digital dictionary of the Serbian language, numbering ~293000 headwords (Wiktionary has ~70000). Furthermore, the entries are annotated with accents, which are frequently missing from other digital dictionaries. \
Unfortunately, it utilized an entirely custom file format, which had to be reverse-engineered. It also won't be getting any updates - some time after 2009 the authors switched to an online-only model. \
Fortunately, C# decompiles easily into readable code 8-)

## Short-term goals
- [x] determine the actual size of the dictionary, to make sure we're not omitting any data
- [x] implement aliases for synonyms ("word1, word2" and "word1 = word2" in the original): invalidated; outputting multiple entries with the same headword Just Works™
- [ ] handle some information from the CSS
- [x] fix lang tags for proper Serbian italics
- [ ] utilize the abbreviations/sources list

## Long-term goals
- [ ] add more output formats
