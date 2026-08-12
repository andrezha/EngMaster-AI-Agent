# Third-Party Data Notices / 第三方数据声明

This notice applies to the 英思成 (RecallLex) vocabulary and independently compiled phrase-data build processes.

## Ministry of Education curriculum standard

The curriculum classification is based on the publicly available document 《普通高中英语课程标准（2017年版2020年修订）》, issued by the Ministry of Education of the People's Republic of China, 教材〔2020〕3号.

Official notice: <https://www.moe.gov.cn/srcsite/A26/s8001/202006/t20200603_462199.html>

The project cites this document as the authoritative curriculum-range source. It does not claim ownership of the curriculum standard or affiliation with the Ministry of Education.

The junior phrase range additionally refers to 《义务教育英语课程标准（2022年版）》, issued by the Ministry of Education, 教材〔2022〕2号.

- Official notice: <https://www.moe.gov.cn/srcsite/A26/s8001/202204/t20220420_619921.html>
- Local source record: `data_sources/raw/moe_junior/source.json`

Both curriculum standards define learning scope and ability requirements. They are not treated as ready-made official phrase lists, and the archived PDFs are not bundled in the customer-facing product.

## CET-4 syllabus

The CET-4 phrase range refers to 《全国大学英语四、六级考试大纲（2016年修订版）》 as listed by the official National Education Examinations Authority CET website.

- Official syllabus page: <https://cet.neea.edu.cn/html1/folder/16113/1588-1.htm>
- Local source record: `data_sources/raw/cet4/source.json`

The syllabus defines the examination ability and vocabulary boundary. The project does not claim that its independently compiled phrases are an official enumerated CET-4 phrase list.

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

## ipa-dict English (General American)

The released 3800-word vocabulary uses the `en_US` dataset from open-dict-data/ipa-dict for General American IPA transcriptions.

- Project: <https://github.com/open-dict-data/ipa-dict>
- Fixed commit: `43c3570eb3553bdd19fccd2bd0091534889af023`
- Selected data: `data/en_US.txt`
- License notice: MIT, Copyright (c) 2016 dohliam
- Local source record: `data_sources/raw/ipa_dict/source.json`
- Product license text: `IPA_DICT_LICENSE.txt`

Of the 3800 released records, 3781 are direct case-insensitive headword matches, 8 use explicit equivalent-spelling mappings, 10 are deterministic compositions from matched source entries, and 1 adds a documented heteronym pronunciation required by the released meanings. These methods are recorded per item in the pronunciation evidence layer. The upstream `en_UK` data is not used because the ipa-dict credits identify it as derived from a GPL-3.0 source.

## Moby Words II and Moby Part-of-Speech II

Moby Words II and Moby Part-of-Speech II by Grady Ward were used for auxiliary spelling and part-of-speech validation.

The archived Project Gutenberg documentation states: “Public Domain material by grant from the author, January, 2001.”

- Moby Words II: <https://www.gutenberg.org/ebooks/3201>
- Moby Part-of-Speech II: <https://www.gutenberg.org/ebooks/3203>
- Local source record: `data_sources/raw/moby/source.json`

## Tatoeba English CC0 sentence subset

Only the English sentences explicitly included in Tatoeba's CC0 export are used as auxiliary phrase-occurrence evidence. The default CC BY sentence export and all audio are excluded from this use.

- Downloads page: <https://tatoeba.org/en/downloads>
- Public-domain dedication: CC0 1.0 Universal
- Local source record: `data_sources/raw/tatoeba/source.json`
- Local legal text: `data_sources/raw/tatoeba/CC0-1.0-legalcode.html`

Tatoeba sentences are not copied into product examples. Raw occurrence counts are not represented as examination frequencies and do not determine learning level.

## No media data

The released vocabulary dataset contains no images or audio. It contains General American IPA transcriptions from the documented ipa-dict build described above. Its Chinese definitions were reorganized and drafted by this project from documented open semantic evidence and checked by automated validation; no claim of item-by-item human review is made.

The released phrase examples were independently written for this product. Tatoeba sentences, default CC BY exports, and audio are not copied into the product.

The complete ECDICT and ipa-dict MIT licenses distributed with this edition are available in `ECDICT_LICENSE.txt` and `IPA_DICT_LICENSE.txt`. The complete Open English WordNet and Creative Commons Attribution 4.0 terms are available in `OPEN_ENGLISH_WORDNET_LICENSE.md`. The underlying Princeton WordNet license is also distributed separately as `PRINCETON_WORDNET_LICENSE.txt`.
