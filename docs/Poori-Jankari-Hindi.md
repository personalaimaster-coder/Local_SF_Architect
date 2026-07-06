# Local SF Architect — पूरी जानकारी (आसान हिंदी में)

> **यह किसके लिए है:** ऐसे किसी भी व्यक्ति के लिए जो यह समझना चाहता है कि यह
> extension असल में करता क्या है, इसके अंदर कौन-कौन से tools (जैसे local DB,
> SQLite, LanceDB आदि) लगे हैं, और हर tool को **क्यों** इस्तेमाल किया गया है।
> सब कुछ सरल हिंदी में, उदाहरण (example) के साथ समझाया गया है।

---

## विषय-सूची (Table of Contents)

1. [एक लाइन में — यह चीज़ है क्या?](#1-एक-लाइन-में--यह-चीज़-है-क्या)
2. [असली समस्या और इसका हल (कहानी के रूप में)](#2-असली-समस्या-और-इसका-हल-कहानी-के-रूप-में)
3. [दो हिस्से — Extension और Engine](#3-दो-हिस्से--extension-और-engine)
4. [MCP क्या है? (सबसे ज़रूरी concept)](#4-mcp-क्या-है-सबसे-ज़रूरी-concept)
5. [7 मुख्य Tools जो AI को मिलते हैं (उदाहरण सहित)](#5-7-मुख्य-tools-जो-ai-को-मिलते-हैं-उदाहरण-सहित)
6. [अंदर लगे सारे technical Tools और उन्हें क्यों चुना गया](#6-अंदर-लगे-सारे-technical-tools-और-उन्हें-क्यों-चुना-गया)
   - [6.1 uv — Python package manager](#61-uv--python-package-manager)
   - [6.2 SQLite — Governor Limits का local database](#62-sqlite--governor-limits-का-local-database)
   - [6.3 LanceDB — Patterns का vector database](#63-lancedb--patterns-का-vector-database)
   - [6.4 fastembed (Embedding Model) — शब्दों को नंबर में बदलना](#64-fastembed-embedding-model--शब्दों-को-नंबर-में-बदलना)
   - [6.5 Reranker (Cross-Encoder) — नतीजों को और सटीक करना](#65-reranker-cross-encoder--नतीजों-को-और-सटीक-करना)
   - [6.6 tree-sitter — Apex code को समझना](#66-tree-sitter--apex-code-को-समझना)
   - [6.7 lxml — Salesforce metadata XML पढ़ना](#67-lxml--salesforce-metadata-xml-पढ़ना)
   - [6.8 FastMCP — MCP server बनाने की library](#68-fastmcp--mcp-server-बनाने-की-library)
   - [6.9 crawl4ai — official docs से नई जानकारी लाना](#69-crawl4ai--official-docs-से-नई-जानकारी-लाना)
   - [6.10 SQLite Audit Log — हर काम का record](#610-sqlite-audit-log--हर-काम-का-record)
7. [Security (सुरक्षा) — आपका code बाहर क्यों नहीं जाता](#7-security-सुरक्षा--आपका-code-बाहर-क्यों-नहीं-जाता)
8. [Confidence Score — जवाब पर कितना भरोसा करें](#8-confidence-score--जवाब-पर-कितना-भरोसा-करें)
9. [आपकी मशीन पर data कहाँ रहता है](#9-आपकी-मशीन-पर-data-कहाँ-रहता-है)
10. [पूरा flow — शुरू से अंत तक एक चित्र में](#10-पूरा-flow--शुरू-से-अंत-तक-एक-चित्र-में)
11. [छोटा सारांश (एक नज़र में)](#11-छोटा-सारांश-एक-नज़र-में)

---

## 1. एक लाइन में — यह चीज़ है क्या?

**Local SF Architect एक पूरी तरह से local (offline) सहायक है जो Salesforce
architects के लिए बना है।**

आसान भाषा में: यह आपके AI editor (जैसे GitHub Copilot, Cursor, या Claude Code) को
कुछ **खास Salesforce के औज़ार (tools)** दे देता है। इन tools की मदद से AI अंदाज़ा
(guess) लगाने की बजाय **पक्का और सही गणित/जवाब** देता है।

**सबसे बड़ी बात:** आपका Salesforce code आपकी मशीन से **कभी बाहर नहीं जाता**।
सारा काम आपके ही laptop पर होता है।

> **उदाहरण:** आप AI से पूछते हैं — "अगर मैं loop में 45,000 rows निकालूँ तो क्या
> Salesforce की limit टूट जाएगी?" — तो normal AI शायद अंदाज़ा लगाकर बता देगा।
> लेकिन यह extension लगा हो तो AI असली Salesforce limit (जैसे 50,000) को एक local
> database से निकालकर सही-सही हिसाब (50,000 − 45,000 = 5,000 बचे) बता देगा।

---

## 2. असली समस्या और इसका हल (कहानी के रूप में)

### पहले क्या दिक्कत थी?

पहले भी यह "engine" (असली दिमाग़) मौजूद था, लेकिन उसे इस्तेमाल करने के लिए हर
developer को खुद से बहुत सारा setup करना पड़ता था:

1. GitHub से पूरा code download (clone) करो।
2. `uv` install करो, फिर कई commands चलाओ।
3. हाथ से एक JSON file (config) में सही रास्ता (path) लिखो।

यह बहुत झंझट भरा काम था। एक normal यूज़र के लिए मुश्किल।

### अब इसका हल क्या है?

एक **VS Code / Cursor extension** बना दिया गया। अब यूज़र को बस इतना करना है:

- Editor खोलो → Extensions में "Local SF Architect" ढूँढो → **Install** दबाओ।
- बाकी सब काम extension **खुद-ब-खुद** कर देता है: engine install करना, AI model
  download करना, local databases बनाना, और सारे agents (Copilot/Cursor/Claude) की
  config अपने-आप set करना।

> **याद रखें:** Extension सिर्फ़ एक छोटा-सा "installer/setup करने वाला" है (लगभग
> 17 KB का)। असली काम Python का "engine" करता है। Extension बस उसे बिना मेहनत के
> लगा देता है।

---

## 3. दो हिस्से — Extension और Engine

पूरे system को समझने के लिए इसे **दो हिस्सों** में देखिए:

| हिस्सा | भाषा | काम | उदाहरण से समझें |
|---|---|---|---|
| **Extension** | TypeScript / Node.js | सिर्फ़ install और setup करना | जैसे किसी मशीन को fit करने वाला mechanic |
| **Engine** | Python | असली दिमाग़ — सारे tools और हिसाब यहीं होते हैं | जैसे असली मशीन जो काम करती है |

**Extension क्या-क्या करता है:**
- `uv` को ढूँढता है (Python चलाने के लिए ज़रूरी)।
- Engine को PyPI से install करता है (`uv tool install sf-local-architect`)।
- AI model download करता है।
- Local databases बनाता है (seed करना)।
- Copilot, Cursor, Claude Code — तीनों की config file अपने-आप ठीक कर देता है।
- नीचे कोने में एक status दिखाता है: **✓ SF Architect**।

**Engine क्या-क्या करता है:**
- वह असली 7 tools जो AI इस्तेमाल करता है (आगे section 5 में)।
- सारे local databases पढ़ना/लिखना।
- Code को parse (समझना) करना।

---

## 4. MCP क्या है? (सबसे ज़रूरी concept)

**MCP = Model Context Protocol।**

यह एक "भाषा" या "नियम" है जिससे कोई AI (जैसे Copilot) किसी बाहरी tool से बात कर
सकता है। सोचिए यह एक **USB port** की तरह है — जैसे किसी भी pen-drive को USB में
लगा सकते हैं, वैसे ही कोई भी MCP tool किसी भी AI में "plug" हो सकता है।

**आसान उदाहरण:**

- आप Cursor में लिखते हैं: *"क्या मेरा code limit तोड़ेगा?"*
- Cursor (AI) सोचता है: "इसके लिए मेरे पास एक tool है — `check_governor_limit`।"
- Cursor उस tool को **MCP के ज़रिए** बुलाता (call) करता है।
- Engine जवाब देता है, और AI आपको साफ़ भाषा में समझा देता है।

यह पूरी बातचीत आपके laptop के अंदर ही होती है — एक process से दूसरी process तक,
बिना internet के (इसे "stdio" यानी standard input/output कहते हैं)।

तीनों AI को अलग-अलग तरीके से जोड़ा जाता है:

| AI Tool | कैसे जुड़ता है |
|---|---|
| **GitHub Copilot (VS Code)** | VS Code की अपनी native MCP API से (कोई JSON file नहीं) |
| **Cursor** | `~/.cursor/mcp.json` file में entry जोड़कर |
| **Claude Code (CLI)** | `claude mcp add` command चलाकर |

---

## 5. 7 मुख्य Tools जो AI को मिलते हैं (उदाहरण सहित)

ये वे असली tools हैं जो engine, AI को देता है। AI आपके सवाल के हिसाब से खुद तय
करता है कि कौन-सा tool चलाना है।

### Tool 1 — `query_architect_db` (सही pattern ढूँढना)

**काम:** एक local knowledge base में से "सबसे अच्छा तरीका (best pattern)" ढूँढता
है। यह शब्द-दर-शब्द नहीं, बल्कि **मतलब** के आधार पर ढूँढता है (semantic search)।

> **उदाहरण:** आप पूछते हैं — *"Salesforce में async processing का सबसे अच्छा
> pattern क्या है?"* → engine LanceDB में से मिलते-जुलते patterns (जैसे Queueable,
> Batch Apple) निकालकर देता है, साथ में यह भी बताता है कि जानकारी कहाँ से आई
> (source) और उस पर कितना भरोसा (confidence) करें।

### Tool 2 — `check_governor_limit` (limit का पक्का हिसाब)

**काम:** Salesforce की असली limits के खिलाफ़ एकदम सही गणित करता है। कोई अंदाज़ा
नहीं — पूरा deterministic (हमेशा एक जैसा सही जवाब)।

> **उदाहरण:** *"क्या 45,000 rows एक transaction में SOQL limit तोड़ेंगी?"* →
> engine SQLite से असली limit (मान लीजिए 50,000) निकालता है और बताता है:
> limit = 50,000, projected = 45,000, बचा हुआ (headroom) = 5,000, टूटेगी? = नहीं।

### Tool 3 — `analyze_local_blast_radius` (क्या-क्या टूटेगा?)

**काम:** अगर आप कोई Apex file बदलेंगे, तो और कौन-कौन सी files प्रभावित होंगी —
यह बताता है। सीधा असर (immediate) और आगे तक का असर (transitive) दोनों।

> **उदाहरण:** *"अगर मैं `AccountService.cls` बदलूँ तो क्या टूटेगा?"* → engine
> आपके पूरे repo को पढ़कर बताता है कि 8 दूसरी files इस class को use करती हैं, तो
> पहले उन्हें check कर लें।

### Tool 4 — `generate_architecture_diagram` (चित्र बनाना)

**काम:** आपके असली code से एक architecture diagram (Mermaid `.md` या draw.io
`.drawio`) बना देता है।

> **उदाहरण:** *"Order subsystem का dependency diagram बनाओ"* → engine एक diagram
> file बना देता है जिसे आप editor में देख सकते हैं।

### Tool 5 — `score_architecture` (सेहत की रिपोर्ट कार्ड)

**काम:** आपके architecture को 4 खंभों (pillars) पर नंबर देता है — Security,
Reliability, Scalability, Performance। और हर नंबर के पीछे **कारण (finding)** भी
बताता है, ताकि नंबर पर भरोसा किया जा सके।

> **उदाहरण:** *"इस project की architecture health बताओ"* → Security: 85/100,
> Performance: 70/100 (क्योंकि loop के अंदर SOQL मिला)... आदि।

### Tool 6 — `set_deliverable_preference` (पसंद याद रखना)

**काम:** आपकी diagram पसंद (Mermaid या draw.io) config में save कर लेता है।

> **उदाहरण:** *"अब से हमेशा draw.io diagram बनाना"* → आगे से हर diagram draw.io
> में बनेगा।

### Tool 7 — `sync_latest_patterns` (नई जानकारी सीखना)

**काम:** किसी official Salesforce docs page से नई जानकारी पढ़कर अपने local
knowledge base में जोड़ लेता है। (Default में बंद, सिर्फ़ भरोसेमंद domains से।)

> **उदाहरण:** *"इस Salesforce docs page से patterns सीखो: `<url>`"* → engine उस
> page को (सुरक्षा जाँच के बाद) पढ़कर patterns database में जोड़ देता है।

---

## 6. अंदर लगे सारे technical Tools और उन्हें क्यों चुना गया

अब सबसे ज़रूरी हिस्सा — **हर tool क्या है और उसे क्यों चुना गया।**

### 6.1 uv — Python package manager

**यह क्या है:** `uv` एक बहुत तेज़ Python package manager है (जैसे `pip` लेकिन कई
गुना तेज़)।

**क्यों इस्तेमाल किया:**
- यह अपने साथ अपना Python भी लेकर आता है — यानी यूज़र को अलग से Python install
  नहीं करना पड़ता।
- बहुत तेज़ है, इसलिए setup जल्दी हो जाता है।
- यही **एकमात्र चीज़** है जो यूज़र को हाथ से install करनी होती है। बाकी सब यह
  अपने-आप कर देता है।

> **उदाहरण:** Extension चलाता है — `uv tool install --upgrade sf-local-architect`।
> इसका मतलब: "engine का नया version install या update कर दो।"

---

### 6.2 SQLite — Governor Limits का local database

**यह क्या है:** SQLite एक छोटा-सा, हल्का database है जो एक ही file में पूरा data
रखता है (कोई server नहीं चलाना पड़ता)।

**क्यों इस्तेमाल किया (बहुत ज़रूरी वजह):**
- Governor limits **पक्के नंबर** हैं (जैसे SOQL limit = 50,000)। इनमें कोई
  "अंदाज़ा" या "मतलब ढूँढना" नहीं चाहिए। इसलिए इन्हें एक साफ़-सुथरी table में रखना
  सबसे सही है।
- SQLite को किसी server, internet, या installation की ज़रूरत नहीं — बस एक file
  (`~/.sf-architect/limits.db`)। यह पूरी तरह local और offline है।
- Query करना एकदम तेज़ और deterministic (हमेशा एक जैसा सही जवाब) है।

**कैसे काम करता है (आसान भाषा में):**
- एक `limits_seed.yaml` file में सारी limits लिखी हैं।
- `seed` command उन्हें SQLite table `limits` में डाल देती है।
- table में columns हैं: `api_version`, `limit_key`, `description`, `value`,
  `unit`, `last_verified`।

> **उदाहरण:** आप पूछते हैं limit_key = "total_soql_queries", api_version = "62.0"।
> SQLite से एक row मिलती है: value = 100। फिर engine हिसाब लगाता है कि आपका
> projected value इससे ऊपर है या नीचे।

```sql
-- यह वही table है जो engine बनाता है:
CREATE TABLE limits (
  api_version   TEXT,   -- जैसे "62.0"
  limit_key     TEXT,   -- जैसे "total_soql_queries"
  value         INTEGER,-- जैसे 100
  unit          TEXT,   -- जैसे "queries"
  last_verified TEXT,   -- कब verify हुआ
  PRIMARY KEY (api_version, limit_key)
);
```

---

### 6.3 LanceDB — Patterns का vector database

**यह क्या है:** LanceDB एक "vector database" है। साधारण database नंबर या text
ढूँढता है, लेकिन vector database **मतलब (meaning)** के आधार पर ढूँढता है।

**क्यों इस्तेमाल किया:**
- "सबसे अच्छा pattern कौन-सा है?" जैसे सवालों का जवाब शब्द-दर-शब्द match से नहीं
  मिलता। आपको **मिलते-जुलते मतलब** वाली जानकारी चाहिए।
- उदाहरण: अगर आप "background job" लिखें और docs में "asynchronous processing" लिखा
  हो — दोनों का मतलब एक जैसा है। Vector search यह समझ लेता है, normal search नहीं।
- LanceDB **embedded** है — यानी SQLite की तरह यह भी बिना server के, सीधे एक folder
  (`~/.sf-architect/data/lance/`) में चलता है। पूरी तरह local।

**कैसे काम करता है (आसान भाषा में):**
1. हर pattern (text) को एक embedding model से 384 नंबरों की एक "list" (vector) में
   बदला जाता है।
2. यह vector LanceDB में save हो जाता है।
3. जब आप सवाल पूछते हैं, तो आपके सवाल का भी vector बनता है।
4. LanceDB उन patterns को ढूँढता है जिनका vector आपके सवाल के vector के "सबसे
   पास" है (cosine distance से नापा जाता है)।

> **उदाहरण:** सवाल "async processing" का vector बना → LanceDB ने वे 5 patterns
> निकाले जिनका मतलब सबसे मिलता-जुलता था (जैसे Queueable Apex, Batch Apex,
> Platform Events) → फिर उन्हें भरोसे (trust) के हिसाब से क्रम में लगा दिया।

---

### 6.4 fastembed (Embedding Model) — शब्दों को नंबर में बदलना

**यह क्या है:** `fastembed` एक library है जो text को "embedding" (नंबरों की list)
में बदलती है। यहाँ model है `BAAI/bge-small-en-v1.5`, जो 384 नंबरों का vector
बनाता है।

**क्यों इस्तेमाल किया:**
- LanceDB को काम करने के लिए हर text का vector चाहिए — वह vector यही model बनाता है।
- यह model **छोटा (~130 MB) और तेज़** है, और CPU पर ही चल जाता है (GPU की ज़रूरत
  नहीं)। इसलिए normal laptop पर भी आराम से चलता है।
- ONNX format का है — यानी बिना भारी frameworks के, हल्के-फुल्के तरीके से चलता है।

**एक बार download, फिर हमेशा offline:**
- Setup के समय यह model एक बार Hugging Face से download होता है।
- उसके बाद यह आपकी मशीन पर cache हो जाता है और बिना internet के चलता है।

> **उदाहरण:** text "bulkify your DML" → model इसे कुछ ऐसे बदल देता है:
> `[0.12, -0.05, 0.88, ... (कुल 384 नंबर)]`। यही "नंबरी रूप" कंप्यूटर को मतलब
> समझने में मदद करता है।

**Embedding cache:** एक ही text बार-बार embed न करना पड़े, इसके लिए engine नतीजे
को cache कर लेता है (तेज़ी के लिए)।

---

### 6.5 Reranker (Cross-Encoder) — नतीजों को और सटीक करना

**यह क्या है:** एक दूसरा, ज़्यादा समझदार model (`Xenova/ms-marco-MiniLM-L-6-v2`,
~80 MB) जो पहले मिले नतीजों को **दोबारा जाँचकर** बेहतर क्रम में लगाता है।

**क्यों इस्तेमाल किया:**
- Vector search तेज़ है पर कभी-कभी क्रम बिलकुल सही नहीं होता। Reranker आपके सवाल
  और हर नतीजे को **एक साथ** पढ़कर सही relevance (कितना काम का है) निकालता है।
- इससे सबसे काम का जवाब सबसे ऊपर आ जाता है — यानी ज़्यादा सटीकता (precision)।
- यह "optional" है — config में `reranker_enabled` से चालू/बंद कर सकते हैं। बंद
  होने पर सिर्फ़ vector score इस्तेमाल होता है।

> **उदाहरण:** LanceDB ने 20 पास वाले patterns निकाले → reranker ने उन 20 को
> आपके असली सवाल के हिसाब से दोबारा तौला → सबसे सही 5 को ऊपर कर दिया।

**दो-कदम वाला तरीका क्यों?** पहले तेज़ तरीके (LanceDB) से बहुत सारे उम्मीदवार
निकालो, फिर धीमे पर सटीक तरीके (reranker) से सिर्फ़ उन थोड़े को छाँटो। इससे तेज़ी
और सटीकता दोनों मिलती हैं।

---

### 6.6 tree-sitter — Apex code को समझना

**यह क्या है:** `tree-sitter` एक "parser" है — यानी यह code को पढ़कर उसका ढाँचा
(structure/AST) समझता है। यहाँ यह Apex (Salesforce की भाषा) को parse करता है।

**क्यों इस्तेमाल किया:**
- सिर्फ़ text ढूँढने (find/replace) से code का सही मतलब नहीं पता चलता। उदाहरण:
  यह जानना कि "क्या SOQL query किसी loop के **अंदर** है" — इसके लिए code का ढाँचा
  समझना ज़रूरी है, सिर्फ़ शब्द ढूँढना काफ़ी नहीं।
- tree-sitter बहुत तेज़ है और थोड़ी-बहुत गड़बड़ी वाले code को भी parse कर लेता है।

**दो जगह इस्तेमाल होता है:**
1. **Blast radius** (`analyze_local_blast_radius`) — कौन-सी class किसे use करती
   है, यह पता करने के लिए।
2. **Linter** (`lint`) — गलत pattern पकड़ने के लिए, जैसे:
   - loop के अंदर SOQL/DML (bulkify करो)।
   - class पर `with sharing` न लिखा हो (security)।
   - बहुत गहरी nesting (4+ level) — code उलझा हुआ है।

> **उदाहरण:** एक file में `for` loop के अंदर `[SELECT ...]` मिला → linter बताता
> है: "SOQL loop के अंदर है; इसे बाहर निकालकर bulkify करो।" (Scalability का issue)

---

### 6.7 lxml — Salesforce metadata XML पढ़ना

**यह क्या है:** `lxml` एक तेज़ library है XML files पढ़ने के लिए।

**क्यों इस्तेमाल किया:**
- Salesforce में सिर्फ़ Apex code नहीं, बहुत सारा **metadata** भी XML files में
  होता है (जैसे objects, fields — `.object-meta.xml`, `.field-meta.xml`)।
- Blast radius निकालते समय यह भी देखना ज़रूरी है कि कौन-सा field किस object का है,
  और कौन उसे reference करता है। यह जानकारी XML में होती है, जिसे `lxml` पढ़ता है।

> **उदाहरण:** `Account.Industry__c.field-meta.xml` से engine समझता है कि यह field
> `Account` object का है → अगर आप इस field को बदलें तो Account से जुड़ी चीज़ें
> प्रभावित हो सकती हैं।

---

### 6.8 FastMCP — MCP server बनाने की library

**यह क्या है:** `fastmcp` एक Python library है जिससे आसानी से MCP server बनाया जा
सकता है।

**क्यों इस्तेमाल किया:**
- यही वह layer है जो हमारे 7 tools को AI के लिए "उपलब्ध" कराती है।
- हर function के ऊपर बस `@mcp.tool` लिख देने से वह function एक ऐसा tool बन जाता है
  जिसे AI बुला सकता है। बहुत सारा जटिल काम यह library खुद संभाल लेती है।
- यह stdio (standard input/output) पर चलता है — यानी कोई network port नहीं खुलता,
  इसलिए सुरक्षा (security) की चिंता कम।

> **उदाहरण (code का ढाँचा):**

```python
mcp = FastMCP("sf-local-architect")

@mcp.tool          # यह इसे AI के लिए एक tool बना देता है
def check_governor_limit(scenario: dict) -> dict:
    ...            # असली हिसाब यहाँ होता है
```

---

### 6.9 crawl4ai — official docs से नई जानकारी लाना

**यह क्या है:** `crawl4ai` एक library है जो web pages को पढ़कर साफ़-सुथरे text
(markdown) में बदल देती है।

**क्यों इस्तेमाल किया:**
- `sync_latest_patterns` tool को किसी Salesforce docs page से नई जानकारी लानी होती
  है। यह library वह page लाकर पढ़ने लायक बना देती है।
- यह **optional** है (`[scrape]` extra) — यानी सिर्फ़ तभी install होती है जब आपको
  यह feature चाहिए। इससे core package हल्का रहता है।

**बहुत ज़रूरी सुरक्षा:** यह feature default में बंद है और सिर्फ़ भरोसेमंद
(allow-listed) Salesforce domains तक ही पहुँच सकता है (जैसे
`developer.salesforce.com`)। हर page सुरक्षा जाँच (नीचे section 7) से गुज़रता है।

---

### 6.10 SQLite Audit Log — हर काम का record

**यह क्या है:** एक और छोटा SQLite database (`~/.sf-architect/logs/audit.db`) जो
हर tool call का record रखता है।

**क्यों इस्तेमाल किया:**
- पारदर्शिता (transparency) के लिए — पता रहे कि कौन-सा tool कब चला, कितनी देर लगी,
  confidence कितनी थी, risk कितना था।
- यह सब **सिर्फ़ आपकी मशीन पर** रहता है, कहीं भेजा नहीं जाता।
- अगर log लिखने में कोई गड़बड़ हो जाए, तो भी असली काम नहीं रुकता (log का fail होना
  tool को नहीं तोड़ता)।

> **उदाहरण:** हर बार जब AI `query_architect_db` चलाता है, एक row जुड़ती है:
> कौन-सा tool, कब (timestamp), कौन-से patterns मिले, confidence = 0.82, समय = 45ms।

---

## 7. Security (सुरक्षा) — आपका code बाहर क्यों नहीं जाता

यह system सुरक्षा को बहुत गंभीरता से लेता है। कुछ खास चीज़ें:

### 7.1 सब कुछ Local है
- Engine आपकी मशीन पर ही चलता है, editor से stdio (pipe) पर बात करता है — कोई
  network port नहीं, कोई login नहीं।
- **आपका Salesforce code कभी बाहर नहीं जाता।**
- सिर्फ़ setup के समय दो internet call होते हैं: (1) PyPI से engine, (2) Hugging
  Face से model। उसके बाद पूरी तरह offline।

### 7.2 Prompt-Injection Guard (धोखे से बचाव)
- कभी-कभी बाहर से लाए गए text में छिपे हुए "बुरे निर्देश" हो सकते हैं (जैसे "पिछले
  सारे निर्देश भूल जाओ" — यह AI को बहकाने की कोशिश होती है)।
- `guard.py` हर बाहरी text को दो बार जाँचता है — एक बार जब वह आता है, और एक बार
  जब वह AI तक जाने वाला होता है। शक होने पर उसे रोक (block) देता है।

> **उदाहरण:** अगर किसी docs page में लिखा हो "ignore all previous instructions"
> तो guard उसे पकड़कर रोक देगा, वह जानकारी database में नहीं जाएगी।

### 7.3 Sanitize + Allowlist + SSRF जाँच
- **Sanitize:** बाहरी text को साफ़ किया जाता है (खतरनाक हिस्से हटाना)।
- **Allowlist:** सिर्फ़ भरोसेमंद domains से ही page लाया जा सकता है।
- **SSRF जाँच:** internal/private addresses पर call नहीं जाने दी जाती (एक आम
  security हमला रोकने के लिए)।

### 7.4 बाहरी जानकारी = "data", "निर्देश" नहीं
- जो भी जानकारी बाहर से आती है, उसे "untrusted reference material" माना जाता है —
  यानी सिर्फ़ पढ़ने की चीज़, न कि मानने वाला आदेश।

---

## 8. Confidence Score — जवाब पर कितना भरोसा करें

जब भी engine pattern ढूँढकर देता है, वह साथ में एक **confidence score** (0 से 1
के बीच) भी देता है — यानी "इस जवाब पर कितना भरोसा करें।"

यह score अंदाज़े से नहीं, बल्कि 4 असली बातों से बनता है:

| बात | वज़न (weight) | मतलब |
|---|---|---|
| **similarity** | 50% | जवाब सवाल से कितना मिलता-जुलता है |
| **source_trust** | 25% | जानकारी का स्रोत कितना भरोसेमंद है |
| **version_match** | 15% | आपके Salesforce version से मेल खाता है या नहीं |
| **corroboration** | 10% | कितने नतीजे एक-दूसरे से सहमत हैं |

अगर score कम (0.5 से नीचे) हो, तो engine साफ़ चेतावनी देता है: "कम भरोसा — इसे
सिर्फ़ शुरुआती बिंदु मानें और source से जाँच लें।"

> **उदाहरण:** एक जवाब का confidence = 0.82 आया → मतलब काफ़ी भरोसेमंद। दूसरे का
> 0.40 आया → engine चेतावनी देगा कि इसे verify कर लें।

---

## 9. आपकी मशीन पर data कहाँ रहता है

सारा local data एक ही जगह रहता है: **`~/.sf-architect/`** (आपकी home directory
में)। यह कभी git में commit नहीं होता।

| जगह (path) | क्या है |
|---|---|
| `~/.sf-architect/limits.db` | SQLite — governor limits का database |
| `~/.sf-architect/data/lance/` | LanceDB — patterns का vector store |
| `~/.sf-architect/logs/audit.db` | SQLite — हर tool call का record |
| `~/.sf-architect/config.yaml` | आपकी settings (diagram पसंद, reranker on/off, आदि) |
| `~/.sf-architect/meta.json` | model/version की जानकारी (schema check के लिए) |
| `~/.sf-architect/diagrams/` | बनाए गए diagrams |

**Schema check (एक अच्छा safety feature):** `meta.json` में यह लिखा होता है कि
database किस model/dimension से बना था। अगर आप engine update करें और model बदल
जाए, तो engine पहले से चेतावनी देता है: "schema mismatch — `rebuild` चलाओ।" इससे
गलत/खराब नतीजे आने से बच जाते हैं।

---

## 10. पूरा flow — शुरू से अंत तक एक चित्र में

```
आप editor (VS Code / Cursor) खोलते हैं
        │
        ▼
Extension अपने-आप चालू होता है
        │
        ├─ 1. uv ढूँढता है
        ├─ 2. engine install करता है (uv tool install sf-local-architect)
        ├─ 3. model download करता है (~130 MB, एक बार)
        ├─ 4. databases बनाता है (seed): SQLite (limits) + LanceDB (patterns)
        └─ 5. Copilot / Cursor / Claude — सबकी config set करता है
        │
        ▼
   Status bar: ✓ SF Architect  (तैयार!)

────────────────────────────────────────────────────────

अब जब आप AI chat में सवाल पूछते हैं:

आप: "AccountService.cls बदलूँ तो क्या टूटेगा?"
        │
        ▼
AI (MCP से) tool बुलाता है: analyze_local_blast_radius
        │
        ▼  (stdio pipe से, आपकी ही मशीन पर)
Python engine चलता है
        │
        ├─ tree-sitter से Apex parse करता है
        ├─ lxml से metadata XML पढ़ता है
        └─ dependency graph बनाकर असर निकालता है
        │
        ▼
नतीजा AI को वापस → AI आपको आसान भाषा में समझाता है
```

---

## 11. छोटा सारांश (एक नज़र में)

| Tool / चीज़ | किस काम के लिए | क्यों चुना गया |
|---|---|---|
| **uv** | Python + engine install करना | तेज़, अपना Python लाता है, यूज़र को कम मेहनत |
| **SQLite (limits.db)** | Governor limits का पक्का database | limits पक्के नंबर हैं; server-free, offline, तेज़ |
| **LanceDB** | Patterns का meaning-based search | "मतलब" से ढूँढना; embedded, offline |
| **fastembed / bge-small** | text → 384-नंबर vector बनाना | छोटा, तेज़, CPU पर चले, offline |
| **Reranker (cross-encoder)** | नतीजों को सटीक क्रम में लगाना | ज़्यादा precision; optional |
| **tree-sitter** | Apex code का ढाँचा समझना | text-search से बेहतर; blast radius + linting |
| **lxml** | Salesforce metadata XML पढ़ना | fields/objects के reference निकालना |
| **FastMCP** | 7 tools को AI के लिए उपलब्ध कराना | आसान MCP server; stdio, सुरक्षित |
| **crawl4ai** | official docs से नई जानकारी लाना | optional; allowlist + security के साथ |
| **SQLite (audit.db)** | हर काम का local record | पारदर्शिता; कुछ बाहर नहीं जाता |
| **Guard + Sanitize + Allowlist** | prompt-injection और खतरों से बचाव | सुरक्षा |
| **Confidence score** | जवाब पर भरोसे का माप | जवाब defensible रहे, अंदाज़ा नहीं |

### सबसे ज़रूरी 3 बातें याद रखें

1. **Extension = installer** (छोटा), **Engine = असली दिमाग़** (Python)।
2. सारे भारी tools (SQLite, LanceDB, models) **आपकी मशीन पर, offline** चलते हैं —
   आपका Salesforce code **कभी बाहर नहीं जाता**।
3. हर tool सोच-समझकर चुना गया है: **पक्के नंबरों के लिए SQLite**, **मतलब ढूँढने
   के लिए LanceDB + embeddings**, **code समझने के लिए tree-sitter/lxml**, और
   **सब कुछ AI से जोड़ने के लिए MCP (FastMCP)**।

---

> **और पढ़ें:** setup के step-by-step निर्देशों के लिए देखें
> [`Getting-Started-New-User.md`](./Getting-Started-New-User.md), और तकनीकी
> बदलावों / publishing के लिए [`Extension-Changes-and-Guide.md`](./Extension-Changes-and-Guide.md).
