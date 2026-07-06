"""Shared realistic benchmark data for RAG component and pipeline tests.

Replaces the trivial 4-sentence world-capitals mock data with a
10-document corpus of factually accurate academic/technical prose
spanning medicine, ML/AI, climate, legal, and technical domains.
"""

from DashAI.back.models.RAG.documents.base_document import BaseDocument
from DashAI.back.models.RAG.documents.chunk import Chunk


# ═══════════════════════════════════════════════════════════════════════
#  _MockDocument
# ═══════════════════════════════════════════════════════════════════════


class _MockDocument(BaseDocument):
    """In-memory document stub for benchmarks — no filesystem needed."""

    def __init__(self, doc_id: int, text: str, file_name: str = "mock.txt"):
        super().__init__(
            id=doc_id,
            file_name=file_name,
            file_path=f"/tmp/{file_name}",
            file_hash=f"hash_{doc_id}",
        )
        self._text = text

    def get_text(self) -> str:
        return self._text

    def get_metadata(self) -> dict:
        return {"source": "mock"}


# ═══════════════════════════════════════════════════════════════════════
#  REALISTIC_CORPUS — 10 factually accurate academic/technical documents
# ═══════════════════════════════════════════════════════════════════════

realistic_doc_0 = (
    "## Type 2 Diabetes Management: Clinical Practice Guidelines\n\n"
    "The management of type 2 diabetes mellitus (T2DM) centers on achieving "
    "glycemic control while minimizing cardiovascular and renal complications. "
    "Current guidelines from the American Diabetes Association (ADA) and the "
    "European Association for the Study of Diabetes (EASD) recommend targeting "
    "a glycated hemoglobin (HbA1c) level below 7.0% for most non-pregnant adults, "
    "though targets should be individualized based on patient factors including "
    "age, comorbidity burden, and hypoglycemia risk.\n\n"
    "Metformin remains the first-line pharmacological therapy due to its efficacy, "
    "safety profile, low cost, and potential cardiovascular benefits. It reduces "
    "hepatic glucose production and improves peripheral insulin sensitivity. "
    "For patients with established atherosclerotic cardiovascular disease (ASCVD), "
    "heart failure, or chronic kidney disease (CKD), guidelines recommend adding "
    "either a sodium-glucose cotransporter-2 (SGLT2) inhibitor or a glucagon-like "
    "peptide-1 (GLP-1) receptor agonist, regardless of HbA1c levels. "
    "SGLT2 inhibitors such as empagliflozin and dapagliflozin have demonstrated "
    "significant reductions in heart failure hospitalizations and CKD progression "
    "in landmark trials including EMPA-REG OUTCOME and DAPA-CKD. GLP-1 receptor "
    "agonists like liraglutide and semaglutide show similar cardiovascular benefits "
    "with the added advantage of weight loss.\n\n"
    "Lifestyle modifications remain foundational: medical nutrition therapy, "
    "at least 150 minutes per week of moderate-intensity aerobic activity, "
    "smoking cessation, and adequate sleep. The combination of pharmacotherapy "
    "and lifestyle intervention yields the greatest reduction in microvascular "
    "and macrovascular outcomes."
)

realistic_doc_1 = (
    "## mRNA Vaccine Technology: From Research to Clinical Application\n\n"
    "Messenger RNA (mRNA) vaccines represent a paradigm shift in vaccinology, "
    "leveraging the body's own cellular machinery to produce antigenic proteins "
    "that trigger an immune response. The technology uses lipid nanoparticles (LNPs) "
    "to encapsulate and deliver synthetic mRNA encoding a target antigen — in the "
    "case of SARS-CoV-2 vaccines, the spike protein — into host cells. Once inside "
    "the cytoplasm, ribosomes translate the mRNA into protein, which is then "
    "displayed on the cell surface and recognized by the immune system, eliciting "
    "both humoral (antibody-mediated) and cellular (T-cell) responses.\n\n"
    "The development timeline was dramatically accelerated by the COVID-19 pandemic. "
    "The Pfizer-BioNTech vaccine (BNT162b2) and the Moderna vaccine (mRNA-1273) "
    "received Emergency Use Authorization from the FDA in December 2020, less than "
    "one year after the SARS-CoV-2 genome was sequenced in January 2020. "
    "This unprecedented speed was enabled by decades of prior research, including "
    "Katalin Kariko and Drew Weissman's discovery that nucleoside-modified mRNA "
    "evades innate immune detection, for which they received the 2023 Nobel Prize "
    "in Physiology or Medicine.\n\n"
    "Compared to traditional vaccines, mRNA platforms offer several advantages: "
    "rapid design and manufacture (no need to culture live virus), inherent safety "
    "(mRNA is non-infectious and transient), and the ability to encode complex "
    "antigens. Ongoing research explores mRNA vaccines for influenza, Zika virus, "
    "cytomegalovirus, and personalized cancer immunotherapies."
)

realistic_doc_2 = (
    "## Attention Is All You Need: The Transformer Architecture\n\n"
    "The Transformer architecture, introduced by Vaswani et al. in the seminal "
    "2017 paper 'Attention Is All You Need,' fundamentally transformed the field "
    "of natural language processing (NLP) and laid the foundation for modern "
    "large language models. Its key innovation is the self-attention mechanism, "
    "which computes a weighted representation of each token in a sequence by "
    "attending to all other tokens simultaneously, eliminating the sequential "
    "computation bottleneck inherent in recurrent neural networks (RNNs) and "
    "long short-term memory (LSTM) networks.\n\n"
    "The architecture consists of an encoder and a decoder, each composed of "
    "stacked layers of multi-head attention and position-wise feed-forward "
    "networks. Multi-head attention allows the model to jointly attend to "
    "information from different representation subspaces at different positions. "
    "Positional encoding, implemented via sinusoidal functions, injects "
    "information about token order since the attention mechanism itself is "
    "permutation-invariant. Layer normalization and residual connections "
    "facilitate training of deep stacks.\n\n"
    "The Transformer's impact on NLP has been profound. BERT (Bidirectional "
    "Encoder Representations from Transformers), introduced by Devlin et al. "
    "in 2018, uses the encoder stack for pre-training on masked language "
    "modeling, achieving state-of-the-art results on a wide range of NLP "
    "benchmarks. GPT (Generative Pre-trained Transformer) and its successors "
    "use the decoder stack for autoregressive language modeling, culminating "
    "in models like GPT-4 that demonstrate emergent reasoning capabilities. "
    "The architecture has since been adapted to computer vision (Vision "
    "Transformer), protein folding (AlphaFold), and multimodal domains."
)

realistic_doc_3 = (
    "## Reinforcement Learning from Human Feedback (RLHF)\n\n"
    "Reinforcement Learning from Human Feedback (RLHF) is a methodology for "
    "aligning language model outputs with human values and preferences. "
    "The approach addresses a fundamental challenge: language models trained "
    "solely on next-token prediction may produce outputs that are factually "
    "incorrect, harmful, or unhelpful, even when statistically probable. "
    "RLHF introduces a human-in-the-loop training stage that fine-tunes the "
    "model's behavior using reinforcement learning.\n\n"
    "The RLHF pipeline consists of three stages. First, a base language model "
    "is fine-tuned on demonstrations of desired behavior (supervised fine-tuning, "
    "or SFT). Second, human annotators rank multiple model outputs for a given "
    "prompt, and these comparisons are used to train a reward model that predicts "
    "human preference scores. Third, the language model policy is optimized using "
    "Proximal Policy Optimization (PPO), a reinforcement learning algorithm that "
    "maximizes the reward model's score while constraining the policy from "
    "deviating too far from the SFT model via a Kullback-Leibler (KL) divergence "
    "penalty. This prevents the phenomenon known as 'reward hacking,' where the "
    "policy exploits idiosyncrasies in the reward model to achieve high scores "
    "without producing genuinely useful outputs.\n\n"
    "RLHF has been instrumental in the development of conversational AI systems "
    "including OpenAI's ChatGPT and Anthropic's Claude. Despite its success, "
    "RLHF faces challenges: human preferences are diverse and culturally "
    "contingent; reward models may encode biases present in annotator populations; "
    "and the PPO optimization can be unstable. Alternative approaches such as "
    "Direct Preference Optimization (DPO) aim to simplify the pipeline by "
    "optimizing directly from preference data without an explicit reward model."
)

realistic_doc_4 = (
    "## Carbon Capture and Storage: Technologies and Challenges\n\n"
    "Carbon capture and storage (CCS) encompasses a suite of technologies "
    "designed to capture carbon dioxide (CO2) emissions from large point "
    "sources such as power plants and industrial facilities, transport the "
    "captured CO2, and inject it into deep geological formations for permanent "
    "storage. The Intergovernmental Panel on Climate Change (IPCC) has "
    "identified CCS as a critical technology for achieving net-zero emissions "
    "by mid-century, particularly for hard-to-abate sectors like cement, "
    "steel, and chemical production.\n\n"
    "Three main capture approaches exist: post-combustion capture separates "
    "CO2 from flue gases after fuel combustion using chemical solvents such "
    "as amines; pre-combustion capture gasifies fuel to produce syngas, from "
    "which CO2 is separated before combustion; and oxyfuel combustion burns "
    "fuel in pure oxygen, producing a flue gas that is nearly pure CO2. "
    "Direct air capture (DAC) is an emerging approach that removes CO2 directly "
    "from ambient air using chemical sorbents or solvents, though it remains "
    "significantly more expensive at $250-600 per ton of CO2 compared to "
    "$50-100 per ton for point-source capture.\n\n"
    "Storage options include deep saline aquifers, depleted oil and gas "
    "reservoirs, and mineralization (reacting CO2 with alkaline minerals to "
    "form stable carbonates). Key challenges include the energy penalty of "
    "capture (reducing net plant efficiency by 5-15 percentage points), the "
    "need for extensive CO2 pipeline infrastructure, and public acceptance "
    "concerns about long-term storage security and induced seismicity."
)

realistic_doc_5 = (
    "## Renewable Energy Integration into Power Grids\n\n"
    "The integration of variable renewable energy (VRE) sources — primarily "
    "solar photovoltaic (PV) and wind power — into existing electrical grids "
    "poses operational, economic, and technical challenges. Unlike dispatchable "
    "fossil fuel plants, VRE generation fluctuates with weather conditions, "
    "creating mismatches between supply and demand that must be managed through "
    "a combination of flexibility resources.\n\n"
    "Energy storage is the cornerstone of VRE integration. Lithium-ion battery "
    "energy storage systems (BESS) provide rapid response for frequency "
    "regulation and short-duration balancing (2-6 hours), with costs declining "
    "from over $1,000 per kWh in 2010 to approximately $150 per kWh in 2023. "
    "For longer-duration storage (days to weeks), pumped hydroelectric storage "
    "remains the dominant technology, accounting for over 90% of global energy "
    "storage capacity. Green hydrogen — produced via electrolysis powered by "
    "renewable electricity — is emerging as a seasonal storage solution and "
    "a decarbonization pathway for industrial processes.\n\n"
    "Smart grid technologies, including advanced metering infrastructure, "
    "demand response programs, and real-time phasor measurement units, enable "
    "dynamic balancing of supply and demand. Germany's Energiewende (energy "
    "transition) serves as a large-scale case study: by 2024, renewable sources "
    "accounted for over 55% of the country's gross electricity consumption. "
    "According to the International Renewable Energy Agency (IRENA), global "
    "renewable capacity reached approximately 3,900 GW in 2023, with solar "
    "PV accounting for the largest share of new additions."
)

realistic_doc_6 = (
    "## General Data Protection Regulation (GDPR): Key Provisions\n\n"
    "The General Data Protection Regulation (Regulation (EU) 2016/679), "
    "commonly known as GDPR, is a comprehensive data protection law enacted "
    "by the European Union that took effect on May 25, 2018. It establishes "
    "a harmonized legal framework for the processing of personal data of "
    "individuals within the European Economic Area (EEA) and has become a "
    "benchmark for privacy legislation worldwide.\n\n"
    "GDPR grants data subjects a set of enforceable rights: the right of "
    "access (Article 15), the right to rectification (Article 16), the right "
    "to erasure or the 'right to be forgotten' (Article 17), the right to "
    "restrict processing (Article 18), the right to data portability (Article "
    "20), and the right to object to processing (Article 21). Organizations "
    "must obtain freely given, specific, informed, and unambiguous consent "
    "for data processing, unless another lawful basis such as legitimate "
    "interest or contractual necessity applies.\n\n"
    "Critically, organizations must notify supervisory authorities of a personal "
    "data breach within 72 hours of becoming aware of it (Article 33). "
    "Non-compliance carries substantial penalties: fines can reach up to "
    "20 million euros or 4% of the undertaking's total worldwide annual "
    "turnover of the preceding financial year, whichever is higher (Article 83). "
    "GDPR's territorial scope extends beyond the EU: it applies to any "
    "organization, regardless of location, that processes the personal data of "
    "individuals in the EEA when offering goods or services to them or "
    "monitoring their behavior (Article 3)."
)

realistic_doc_7 = (
    "## Open Source Software Licensing: A Comparative Analysis\n\n"
    "Open source software licenses establish the legal terms under which "
    "software may be used, modified, and distributed. Licenses fall along a "
    "spectrum from highly permissive to strongly protective (copyleft), and "
    "the choice of license has significant implications for commercial "
    "software development.\n\n"
    "The MIT License is among the most permissive: it allows unrestricted use, "
    "modification, distribution, and sublicensing, requiring only that the "
    "original copyright notice and permission notice be included. The Apache "
    "License 2.0 is similarly permissive but adds an explicit grant of patent "
    "rights from contributors to users, providing additional legal protection "
    "against patent litigation. BSD licenses (2-Clause and 3-Clause) are "
    "comparable to MIT in permissiveness.\n\n"
    "At the other end of the spectrum, the GNU General Public License (GPL) "
    "embodies the principle of copyleft: any derivative work or software that "
    "incorporates GPL-licensed code must itself be distributed under the GPL. "
    "This 'viral' provision ensures that modifications remain open but can "
    "create compliance challenges for proprietary software. The GNU Lesser GPL "
    "(LGPL) provides a middle ground: it permits linking from proprietary "
    "software without triggering copyleft obligations, making it suitable for "
    "shared libraries. For startups and commercial entities, the choice between "
    "permissive and copyleft licenses involves balancing community contributions "
    "against the ability to maintain proprietary competitive advantages."
)

realistic_doc_8 = (
    "## Microservices Architecture: Design Patterns and Anti-Patterns\n\n"
    "Microservices architecture is an approach to software development in which "
    "an application is structured as a collection of independently deployable, "
    "loosely coupled services. Each service encapsulates a specific business "
    "capability, owns its own data store, and communicates with other services "
    "through well-defined APIs — typically REST over HTTP or asynchronous "
    "messaging.\n\n"
    "Several design patterns have emerged to address common challenges. "
    "The API Gateway pattern provides a single entry point for client requests, "
    "handling cross-cutting concerns such as authentication, rate limiting, "
    "and request routing. Service discovery enables services to locate each "
    "other dynamically in containerized environments where IP addresses change "
    "frequently. The Circuit Breaker pattern prevents cascading failures by "
    "detecting when a downstream service is unresponsive and failing fast "
    "rather than accumulating blocked threads. Event-driven communication via "
    "message brokers (e.g., Apache Kafka, RabbitMQ) enables asynchronous, "
    "eventually consistent interactions that improve resilience and scalability.\n\n"
    "Containerization, particularly with Docker, has become the de facto "
    "deployment unit for microservices, and Kubernetes has emerged as the "
    "dominant orchestration platform. Common anti-patterns include the "
    "distributed monolith — where services are technically separate but tightly "
    "coupled through shared databases or synchronous call chains — and data "
    "inconsistency arising from the loss of ACID transactions across service "
    "boundaries, requiring careful design of sagas and eventual consistency."
)

realistic_doc_9 = (
    "## Database Query Optimization: Indexing Strategies\n\n"
    "Database indexes are data structures that improve the speed of data "
    "retrieval operations at the cost of additional storage and write "
    "overhead. Proper index design is one of the most impactful performance "
    "optimizations available to application developers, yet poor indexing "
    "choices can degrade performance substantially.\n\n"
    "The B-tree (balanced tree) index is the default and most widely used "
    "index type in relational databases including PostgreSQL and MySQL's "
    "InnoDB storage engine. It maintains sorted data and supports equality "
    "and range queries efficiently with O(log n) lookup time. Composite "
    "indexes index multiple columns together and are most effective when "
    "queries filter on the leading (leftmost) columns — a principle known "
    "as the leftmost prefix rule. Covering indexes include all columns "
    "referenced by a query, allowing the database to satisfy the query "
    "entirely from the index without accessing the table (an index-only scan).\n\n"
    "Query execution plans, inspected via the EXPLAIN command, reveal how "
    "the database engine executes a query: whether it uses sequential scans "
    "or index scans, the estimated row counts, and join strategies. Index "
    "selectivity — the proportion of rows matching a given value — determines "
    "whether the query planner will use an index; low-selectivity indexes "
    "are often ignored in favor of full table scans. Partial indexes reduce "
    "index size by indexing only rows satisfying a WHERE clause. The trade-off "
    "is fundamental: each additional index accelerates reads but slows writes "
    "(INSERT, UPDATE, DELETE) because the index must be maintained. Common "
    "pitfalls include over-indexing, unused indexes consuming storage and "
    "write capacity, and neglecting to analyze tables for up-to-date statistics."
)


REALISTIC_CORPUS: dict[int, str] = {
    0: realistic_doc_0,
    1: realistic_doc_1,
    2: realistic_doc_2,
    3: realistic_doc_3,
    4: realistic_doc_4,
    5: realistic_doc_5,
    6: realistic_doc_6,
    7: realistic_doc_7,
    8: realistic_doc_8,
    9: realistic_doc_9,
}


def make_corpus_documents() -> dict[int, _MockDocument]:
    """Build _MockDocument instances from REALISTIC_CORPUS."""
    return {doc_id: _MockDocument(doc_id, text) for doc_id, text in REALISTIC_CORPUS.items()}


# ═══════════════════════════════════════════════════════════════════════
#  CORPUS_QA_PAIRS — 12 domain-specific question-answer pairs
# ═══════════════════════════════════════════════════════════════════════

CORPUS_QA_PAIRS: list[dict] = [
    {
        "query": "What is the recommended first-line medication for type 2 diabetes?",
        "hint": "metformin",
        "doc_ids": [0],
    },
    {
        "query": "What mechanism do mRNA vaccines use to deliver genetic material into cells?",
        "hint": "lipid nanoparticles",
        "doc_ids": [1],
    },
    {
        "query": "What algorithm is commonly used in RLHF to optimize the language model policy?",
        "hint": "PPO",
        "doc_ids": [3],
    },
    {
        "query": "What is the maximum fine under GDPR for non-compliance?",
        "hint": "4%",
        "doc_ids": [6],
    },
    {
        "query": "What is the primary difference between MIT and GPL licenses?",
        "hint": "copyleft",
        "doc_ids": [7],
    },
    {
        "query": "Compare the challenges of carbon capture technologies with the challenges of renewable energy integration.",
        "hint": "energy penalty",
        "doc_ids": [4, 5],
    },
    {
        "query": "How do the Transformer architecture and RLHF relate to each other in modern AI systems?",
        "hint": "fine-tune",
        "doc_ids": [2, 3],
    },
    {
        "query": "Based on the GDPR framework, what obligations would a US-based cloud storage company have if it stores personal data of EU residents?",
        "hint": "territorial scope",
        "doc_ids": [6],
    },
    {
        "query": "What trade-offs exist between permissive and copyleft open source licenses for a startup building commercial software?",
        "hint": "proprietary",
        "doc_ids": [7],
    },
    {
        "query": "What design pattern helps prevent cascading failures in a microservices architecture?",
        "hint": "Circuit Breaker",
        "doc_ids": [8],
    },
    {
        "query": "Explain the trade-off between read performance and write performance when adding database indexes.",
        "hint": "write overhead",
        "doc_ids": [9],
    },
    {
        "query": "Contrast the development timeline of traditional vaccines with mRNA vaccines.",
        "hint": "one year",
        "doc_ids": [1],
    },
]

# ═══════════════════════════════════════════════════════════════════════
#  MULTI_TURN_CONVERSATION
# ═══════════════════════════════════════════════════════════════════════

MULTI_TURN_CONVERSATION = [
    {
        "role": "user",
        "content": "Can you summarize the key clinical guidelines for managing type 2 diabetes?",
    },
    {
        "role": "assistant",
        "content": (
            "Based on the provided document, the key guidelines include: targeting "
            "HbA1c below 7% for most adults, using metformin as first-line "
            "pharmacological therapy, and emphasizing lifestyle modifications "
            "including diet and exercise. Additionally, SGLT2 inhibitors and GLP-1 "
            "receptor agonists are recommended for patients with established "
            "cardiovascular disease due to their proven cardiovascular benefits."
        ),
    },
    {
        "role": "user",
        "content": "What are the cardiovascular benefits of SGLT2 inhibitors specifically?",
    },
    {
        "role": "assistant",
        "content": (
            "SGLT2 inhibitors have demonstrated significant cardiovascular benefits "
            "in clinical trials. They reduce the risk of major adverse cardiovascular "
            "events (MACE) by approximately 14%, decrease hospitalization for heart "
            "failure by 35%, and slow the progression of chronic kidney disease. "
            "These benefits appear to be independent of their glucose-lowering effects."
        ),
    },
    {
        "role": "user",
        "content": "How do these compare to the benefits of GLP-1 receptor agonists?",
    },
]

# ═══════════════════════════════════════════════════════════════════════
#  CHUNKING_DOCUMENT — structured document for chunker testing
# ═══════════════════════════════════════════════════════════════════════

CHUNKING_DOCUMENT = (
    "## 1. Introduction\n\n"
    "Retrieval-Augmented Generation (RAG) systems have emerged as a powerful "
    "paradigm for grounding large language model (LLM) outputs in external "
    "knowledge sources. By retrieving relevant document chunks before generation, "
    "RAG systems reduce hallucination, enable attribution, and allow models to "
    "access information beyond their training cutoff. However, the performance "
    "of RAG systems varies substantially depending on the choice of chunking "
    "strategy, embedding model, retrieval algorithm, and prompt template. "
    "Systematic benchmarking of these components is essential for understanding "
    "the trade-offs involved in RAG system design.\n\n"
    "## 2. Methodology\n\n"
    "We propose a modular benchmarking framework that evaluates each pipeline "
    "stage independently and in combination. The framework supports three "
    "chunking strategies: character-based splitting with configurable overlap, "
    "recursive character splitting with separator hierarchies, and token-based "
    "splitting using model-specific tokenizers. For retrieval, we evaluate "
    "sparse methods (BM25, TF-IDF), dense methods using various embedding "
    "models (SentenceTransformers, BERT, E5, and others), and composite "
    "methods including reciprocal rank fusion and maximal marginal relevance "
    "(MMR) reranking. The generator stage tests local GGUF-quantized models "
    "(Llama, Mistral, Qwen, SmolLM, Phi) as well as API-based models.\n\n"
    "Each configuration is evaluated on a corpus of ten domain-specific "
    "documents spanning medicine, climate science, law, and software "
    "engineering, with twelve hand-crafted question-answer pairs covering "
    "factoid extraction, multi-document synthesis, inference, and comparison. "
    "Metrics include retrieval precision at various values of k, generation "
    "faithfulness as measured by entailment against source chunks, and "
    "end-to-end latency.\n\n"
    "## 3. Results\n\n"
    "Our experiments reveal that recursive character chunking with a 1,000 "
    "character window and 100 character overlap provides the best balance of "
    "context preservation and retrieval granularity across document types. "
    "Dense retrieval with SentenceTransformer embeddings (all-MiniLM-L6-v2) "
    "consistently outperforms sparse BM25 retrieval for semantic queries, though "
    "BM25 maintains an advantage for keyword-matching queries. Composite "
    "retrieval with MMR reranking improves diversity at a small latency cost. "
    "The largest local model tested (Llama 3.2 3B at Q4_K_M quantization) "
    "achieves 84% faithfulness on factoid queries but degrades to 62% on "
    "multi-document synthesis tasks, highlighting the challenge of integrating "
    "information from multiple sources.\n\n"
    "## 4. Discussion\n\n"
    "The benchmarking results underscore the importance of component-level "
    "evaluation: end-to-end metrics alone can mask significant weaknesses in "
    "individual pipeline stages. For instance, a strong generator can compensate "
    "for poor retrieval on simple queries, but this compensation fails on "
    "knowledge-intensive tasks where retrieval precision is paramount. We "
    "recommend that RAG system developers adopt a layered evaluation strategy "
    "that measures retrieval quality, generation faithfulness, and end-to-end "
    "accuracy independently. Future work should incorporate multilingual "
    "corpora, streaming evaluation, and more sophisticated faithfulness "
    "metrics such as claim-level entailment verification."
)

# ═══════════════════════════════════════════════════════════════════════
#  build_test_chunks
# ═══════════════════════════════════════════════════════════════════════


def build_test_chunks(doc_ids: list[int] | None = None, chunk_size: int = 200) -> dict:
    """Build test chunks from REALISTIC_CORPUS documents.

    Simple character-based splitting into chunks of approx chunk_size.
    Returns {doc_id: {chunk_id: Chunk}} format expected by retrievers.

    Parameters
    ----------
    doc_ids : list[int] | None
        Document IDs to include. If None, uses all 10 documents.
    chunk_size : int
        Approximate characters per chunk.

    Returns
    -------
    dict
        Nested dict: {doc_id: {chunk_position: Chunk}}.
    """
    if doc_ids is None:
        doc_ids = list(REALISTIC_CORPUS.keys())

    chunks: dict = {}
    chunk_idx = 0
    for doc_id in doc_ids:
        text = REALISTIC_CORPUS[doc_id]
        # Split into sentences roughly, then group into chunks
        sentences = [s.strip() for s in text.replace("\n", " ").split(". ")]
        doc_chunks = {}
        current_chunk = ""
        pos = 0
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
                doc_chunks[pos] = Chunk(
                    id=chunk_idx,
                    document_id=str(doc_id),
                    document_position=pos,
                    text=current_chunk.strip() + ".",
                )
                chunk_idx += 1
                pos += 1
                current_chunk = sentence
            else:
                current_chunk = (current_chunk + ". " + sentence) if current_chunk else sentence
        if current_chunk:
            doc_chunks[pos] = Chunk(
                id=chunk_idx,
                document_id=str(doc_id),
                document_position=pos,
                text=current_chunk.strip() + ".",
            )
            chunk_idx += 1
        chunks[doc_id] = doc_chunks

    return chunks


# ═══════════════════════════════════════════════════════════════════════
#  Component import maps (shared across benchmark files)
# ═══════════════════════════════════════════════════════════════════════

LLM_MAP = {
    "LlamaModel": (
        "DashAI.back.models.hugging_face.llama_model",
        "LlamaModel",
    ),
    "MistralModel": (
        "DashAI.back.models.hugging_face.mistral_model",
        "MistralModel",
    ),
    "QwenModel": (
        "DashAI.back.models.hugging_face.qwen_model",
        "QwenModel",
    ),
    "SmolLMModel": (
        "DashAI.back.models.hugging_face.smol_lm_model",
        "SmolLMModel",
    ),
    "Phi4MiniInstructModel": (
        "DashAI.back.models.hugging_face.phi_4_mini_instruct_model",
        "Phi4MiniInstructModel",
    ),
}

EMBEDDING_MAP = {
    "SentenceTransformerEmbedding": (
        "DashAI.back.models.RAG.embeddings.dense.sentence_transformer_embedding",
        "SentenceTransformerEmbedding",
    ),
    "BERTEmbedding": (
        "DashAI.back.models.RAG.embeddings.dense.bert_embedding",
        "BERTEmbedding",
    ),
    "DistilBERTEmbedding": (
        "DashAI.back.models.RAG.embeddings.dense.distilbert_embedding",
        "DistilBERTEmbedding",
    ),
    "RoBERTaEmbedding": (
        "DashAI.back.models.RAG.embeddings.dense.roberta_embedding",
        "RoBERTaEmbedding",
    ),
    "E5Embedding": (
        "DashAI.back.models.RAG.embeddings.dense.e5_embedding",
        "E5Embedding",
    ),
    "GemmaEmbedding": (
        "DashAI.back.models.RAG.embeddings.dense.gemma_embedding",
        "GemmaEmbedding",
    ),
    "InstructorEmbedding": (
        "DashAI.back.models.RAG.embeddings.dense.instructor_embedding",
        "InstructorEmbedding",
    ),
    "LaBSEmbedding": (
        "DashAI.back.models.RAG.embeddings.dense.labse_embedding",
        "LaBSEmbedding",
    ),
    "FastTextEmbedding": (
        "DashAI.back.models.RAG.embeddings.dense.fasttext_embedding",
        "FastTextEmbedding",
    ),
    "OpenAIEmbedding": (
        "DashAI.back.models.RAG.embeddings.dense.openai_embedding",
        "OpenAIEmbedding",
    ),
}

CHUNKER_MAP = {
    "CharacterChunkModel": (
        "DashAI.back.models.RAG.chunking_models.character_chunk_model",
        "CharacterChunkModel",
    ),
    "RecursiveCharacterChunkModel": (
        "DashAI.back.models.RAG.chunking_models.recursive_character_chunk_model",
        "RecursiveCharacterChunkModel",
    ),
    "TokenChunkModel": (
        "DashAI.back.models.RAG.chunking_models.token_chunk_model",
        "TokenChunkModel",
    ),
}

PROMPT_MAP = {
    "DefaultRAGGenerationPrompt": (
        "DashAI.back.models.RAG.prompts.generation.default_rag_generation_prompt",
        "DefaultRAGGenerationPrompt",
    ),
    "DefaultQnARAGGenerationPrompt": (
        "DashAI.back.models.RAG.prompts.generation.default_qna_rag_generation_prompt",
        "DefaultQnARAGGenerationPrompt",
    ),
    "CustomRAGGenerationPrompt": (
        "DashAI.back.models.RAG.prompts.generation.custom_rag_generation_prompt",
        "CustomRAGGenerationPrompt",
    ),
}

# ═══════════════════════════════════════════════════════════════════════
#  Legacy backward-compatible data
# ═══════════════════════════════════════════════════════════════════════

BENCHMARK_TEXT = (
    "Paris is the capital of France. It is known for the Eiffel Tower. "
    "Berlin is the capital of Germany. It is known for the Brandenburg Gate. "
    "Tokyo is the capital of Japan. It is known for its technology and temples. "
    "London is the capital of the United Kingdom. It is known for Big Ben."
)

TEST_CHUNKS = {
    0: {
        i: Chunk(id=i, document_id="0", document_position=i, text=t)
        for i, t in enumerate(
            [
                "Paris is the capital of France. It is known for the Eiffel Tower.",
                "Berlin is the capital of Germany. Known for the Brandenburg Gate.",
                "Tokyo is the capital of Japan. Known for its temples and technology.",
                "London is the capital of the UK. Known for Big Ben and the Thames.",
                "Madrid is the capital of Spain. Known for its art museums and food.",
                "Ottawa is the capital of Canada. Known for its parliament buildings.",
            ]
        )
    }
}
