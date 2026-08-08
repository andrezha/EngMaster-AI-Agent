# Third-Party Data Notices / 第三方数据声明

This notice applies to the EngMaster vocabulary data build process. The current 3,800-record English headword master intentionally contains no Chinese definitions or phonetics.

## Ministry of Education curriculum standard

The curriculum classification is based on the publicly available document 《普通高中英语课程标准（2017年版2020年修订）》, issued by the Ministry of Education of the People's Republic of China, 教材〔2020〕3号.

Official notice: <https://www.moe.gov.cn/srcsite/A26/s8001/202006/t20200603_462199.html>

The project cites this document as the authoritative curriculum-range source. It does not claim ownership of the curriculum standard or affiliation with the Ministry of Education.

## Open English WordNet 2025

Open English WordNet 2025 was used for lemma, part-of-speech, sense-presence and semantic-class validation.

This resource is derived from Princeton WordNet under the WordNet License and further developed by the Open English WordNet Team under the Creative Commons Attribution 4.0 International License.

- Open English WordNet: <https://en-word.net/>
- CC BY 4.0: <https://creativecommons.org/licenses/by/4.0/>
- Princeton WordNet license: <https://wordnet.princeton.edu/license-and-commercial-use>
- Attribution: Princeton WordNet and the Open English WordNet Team
- Local full license text: `data_sources/raw/oewn/LICENSE.md`

## ECDICT

ECDICT Free English to Chinese Dictionary Database was used only for exact word lookup, audit tags, and BNC/contemporary-corpus rank metadata during selection. Chinese translations, definitions, phonetics, details and audio fields were not extracted into the current headword master.

- Project: <https://github.com/skywind3000/ECDICT>
- Fixed commit: `bc015ed2e24a7abef49fc6dbbb7fe32c1dadaf8b`
- License: MIT
- Copyright notice in the archived license: Copyright (c) 2025 Linwei
- Local full license text: `data_sources/raw/ecdict/LICENSE`

The MIT copyright and permission notice must be retained with copies or substantial portions of the ECDICT material.

## Moby Words II and Moby Part-of-Speech II

Moby Words II and Moby Part-of-Speech II by Grady Ward were used for auxiliary spelling and part-of-speech validation.

The archived Project Gutenberg documentation states: “Public Domain material by grant from the author, January, 2001.”

- Moby Words II: <https://www.gutenberg.org/ebooks/3201>
- Moby Part-of-Speech II: <https://www.gutenberg.org/ebooks/3203>
- Local source record: `data_sources/raw/moby/source.json`

## No media data

The vocabulary dataset described by this notice contains no images and no audio. The current frozen English headword master also contains no Chinese definitions and no phonetic transcriptions; those fields are intentionally blank pending a separately documented build stage.
