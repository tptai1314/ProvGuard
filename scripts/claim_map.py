#!/usr/bin/env python3
"""Build citation_claim_map.csv: one row per cited reference, joining bib
metadata with the manuscript claim it supports and the verification record
from audit/lit*_report.md."""
import re, csv, os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bib = open(os.path.join(root,'references_verified.bib')).read()
def entries():
    out={}
    for m in re.finditer(r'@(\w+)\{([^,]+),(.*?)\n\}', bib, re.S):
        typ,key,body=m.groups(); f={}
        for fm in re.finditer(r'(\w+)\s*=\s*\{(.*?)\}\s*,?\s*$', body, re.M): f[fm.group(1).lower()]=fm.group(2).strip('{}')
        f['_type']=typ; out[key]=f
    return out
E=entries()
FT='full-text verified'; AO='abstract-only verified'; MD='metadata-only, not used for substantive claims'; DOC='full-text verified (documentation page)'
# key: (verification source, level, sections, claim, location)
C={
'deivasigamani2026nota11y':('arxiv.org/html/2608.08939v1',FT,'Intro; RW 2.2; Sec 3; Sec 8; App B','Nine accessibility-exposed vectors A1-A9; aggregate ASR 0.822 (MobileRun+Gemma4:31B); provenance recommendation quote; 5 trials per vector','Abstract; Sec 3.3; Sec 4/Tables 2,4; Sec 7.1'),
'chen2026mobileworldsafety':('arxiv.org/html/2608.17659v1',FT,'Intro; RW 2.2; Sec 8','ASR 40.4-66.9% over six models on 142 risk tasks, 13 apps, 5 vectors; defensive system prompt mainly converts attacks into stalled tasks (2->20); defense treats environmental content as untrusted','Abstract; Sec 4; Sec 5/Table 2'),
'li2026uidesync':('arxiv.org/html/2609.16732v1',FT,'Intro; RW 2.2; Sec 3; Sec 5.1; Sec 8','Definition of human-agent UI desynchronization; 66.9% dynamic MR on repackaged APKs; 88.7% of 186 participants failed to notice; occlusion/contrast/a11y-only mechanisms; 546 tasks, 13 apps','Abstract; Sec 2.2.2; Sec 4.4; Sec 5; Sec 5.5'),
'liu2026agenthazard':('arxiv.org/pdf/2507.04227v2; MobiSys 2026 program; OpenAlex DOI record',FT,'Intro; RW 2.2; Sec 3; Sec 5.1; Sec 8; Sec 10','Average misleading rate 42.0% dynamic / 36.1% static; 122 tasks, >3000 scenarios; only third-party-writable regions modified; quote that OSes should provide APIs to annotate GUI elements with source metadata; AWAttackerApplier','Abstract; Sec 3 threat model; Sec 7 Discussion'),
'du2025measuringmobileagents':('arxiv.org/pdf/2510.27140v1',FT,'Intro; RW 2.2; Sec 3; Sec 8','Fraudulent ads >80% reliability; 8 agents; entry points banner/interstitial/app-open ads, WebView, e-mail and messaging notifications; interstitial ads E=93.75%','Abstract; Sec 3.1; Table 4'),
'qian2026zeropermission':('arxiv.org/html/2601.12349v1',FT,'Intro; RW 2.2; Sec 3; Sec 5.4; Sec 7; Sec 8','Action rebinding via foreground switch in observe-to-act gap (4.18-15.43 s); 100% atomic rebinding on 6 agents; root cause quote (no binding to process handle/component identity); visual atomicity; 15 tasks in 5 domains','Abstract; Sec 4; Table 2; Table 5'),
'xu2026pusv':('arxiv.org/html/2604.18860v1',FT,'RW 2.2; Sec 5.4; Table 1','PUSV: pre-dispatch UI state re-verification (masked pixel SSIM, screenshot diff, X-window diff) on desktop; blind spot for zero-visual-footprint DOM injection','Abstract; Sec 5.1'),
'liu2026visualconfuseddeputy':('arxiv.org/html/2603.14707v1',FT,'RW 2.2; Table 1','Definition of visual confused deputy event; dual-channel learned guardrail outside agent process; desktop','Sec 2 Def. 1; Sec 4'),
'chen2025ghosteibench':('arxiv.org/html/2510.20333v2',FT,'Intro; RW 2.2; Sec 3; Sec 8','110 test cases, 14 apps, overlays and pop-up SMS; VR 16.43-56.25%; cautious prompting reduces VR 54.88%->47.50%','Sec 3; Table 1; App D.2'),
'sun2026ossentinel':('arxiv.org/html/2510.24411v3; aclanthology.org/2026.acl-long.431',FT,'RW 2.3; Table 1; Sec 8 (B4)','Hybrid formal verifier + VLM judge at step and trajectory level; no attribution to content origin; VLM judge in decision path','Sec 4; Sec 4.2'),
'zou2026aura':('arxiv.org/html/2602.10915v3',FT,'Intro; RW 2.3; Table 1; Sec 8 (B3)','TAG_VERIFIED/TAG_TAINTED with no-write-down into critical operations; simulated device with structured mock APIs','Sec 4.3.1; Sec 5.1.2'),
'zhao2026aohp':('arxiv.org/html/2606.23449v1',FT,'Intro; RW 2.3; Table 1; Sec 8 (B3)','Real AOSP agent harness; typed placeholders and taint metadata for sensitive data (confidentiality); no injection evaluation','Abstract; Sec 6.2; Sec 6.4; Sec 7.3'),
'debenedetti2025camel':('arxiv.org/html/2503.18813v2; author publication page (SaTML 2026)',FT,'Intro; RW 2.3; Table 1; Sec 9','Control/data flow extracted from trusted query so untrusted data cannot impact program flow; capabilities on values; data-requires-action failure mode','Abstract; Sec 5.1; Sec 5.3; Sec 6.1.2'),
'costa2025fides':('arxiv.org/html/2505.23643v2',FT,'Intro; RW 2.3; Table 1; Sec 9','Confidentiality and integrity labels on all data; deterministic policy enforcement; non-interference guarantee for integrity of consequential actions','Abstract; Sec 4.4'),
'siddiqui2025permissive':('arxiv.org/pdf/2410.03055v2; mlanthology TMLR 2025',FT,'RW 2.3','Propagate only labels of influential inputs, influence tested by substituting the context','Abstract; Sec 3 (Prop. 1)'),
'cai2026neurotaint':('arxiv.org/pdf/2604.23374v1',FT,'RW 2.3; Table 1','Taint tracking for LLM agents with provenance graph, semantic matching, and LLM-based causal analyzer','Abstract; Sec 4'),
'shim2026flowseal':('arxiv.org/html/2609.14003v1',FT,'RW 2.3; Sec 9','Quote: enforcement by LLM judgment coincides with attack surface; interceptor outside LLM context with provenance-derived lattice (confidentiality)','Abstract; design section'),
'kravchenko2026appa':('arxiv.org/html/2607.24625v1 (Sec 1-6)',FT,'RW 2.3','IFC with context branching to confine taint while preserving utility (tool-calling agents)','Abstract; Sec 3'),
'zhu2025melon':('arxiv.org/pdf/2502.05174v4; PMLR v267 page',FT,'Intro; RW 2.3; Table 1; Sec 7; Sec 9','Masked re-execution with task-neutral prompt; flags attack when tool calls similar; doubles model calls; temperature 0; Hoeffding-type ensemble bound under separation assumption','Abstract; Sec 3.3; Sec 3.4.2; Sec 4 setup'),
'li2026ace':('arxiv.org/html/2504.20984v3; NDSS 2026 accepted papers; DOI',FT,'Intro; RW 2.3; Table 1; Sec 9','Abstract plan from trusted user query only; concrete plan checked against it and a lattice-based IFC policy','Abstract; Sec 4'),
'wu2025isolategpt':('NDSS 2025 camera-ready PDF; DOI',FT,'RW 2.3','Hub-and-spoke execution isolation with deterministic non-LLM operators','Sec 4 design'),
'hines2024spotlighting':('arxiv.org/html/2403.14720v1',FT,'RW 2.3; Table 1; Sec 8 (B1)','Spotlighting gives a continuous provenance signal via delimiting/datamarking/encoding (quote)','Abstract; Sec III'),
'shi2025progent':('arxiv.org/html/2504.11703v3',FT,'RW 2.3','Least-privilege policies over tool names and arguments checked deterministically','Abstract'),
'chen2025struq':('usenix.org USENIX Security 25 page; arXiv v2',FT,'Intro; RW 2.3','Separating instruction and data channels via secure front-end and fine-tuned model','Abstract; Sec 4'),
'chen2025secalign':('Crossref DOI record; arXiv v3',FT,'Intro; RW 2.3','Preference optimization against prompt injection (requires training)','Abstract'),
'wallace2024instruction':('arxiv.org/html/2404.13208v1',FT,'Intro; RW 2.3','Training models to prioritize privileged instructions over tool outputs and instructions in images','Abstract; Sec 3.1'),
'liu2024formalizing':('usenix.org USENIX Security 24 page; arXiv v5',FT,'RW 2.2; RW 2.3','Formal definition of prompt injection; no existing prevention-based defense sufficient (incl. delimiters)','Sec 4.1 Def. 1; Sec 6'),
'wen2024autodroid':('Crossref DOI; MSR camera-ready PDF',FT,'RW 2.1; RW 2.3','Simplified HTML GUI representation; 71.3% success on 158 tasks; LLM-identified risky actions require user confirmation','Abstract; GUI representation section; risky-action section'),
'denning1976lattice':('Crossref DOI 10.1145/360051.360056','metadata + well-known content (abstract-level)','RW 2.4; Sec 4','Lattice model of secure information flow','Abstract'),
'biba1977integrity':('DTIC ADA039324 full text',FT,'RW 2.4; Sec 4','Integrity-oriented (dual) ordering of labels','Report body'),
'goguen1982noninterference':('Crossref/OpenAlex DOI 10.1109/SP.1982.10014',AO,'RW 2.4','Definition of non-interference','Abstract'),
'sabelfeld2003language':('Crossref DOI 10.1109/JSAC.2002.806121',AO,'RW 2.4','Survey of language-based information-flow security','Abstract'),
'myers1997decentralized':('Crossref DOI 10.1145/268998.266669',AO,'RW 2.4','Decentralized label model for information flow control','Abstract'),
'krohn2007flume':('OpenAlex DOI 10.1145/1294261.1294293',AO,'RW 2.4','DIFC on standard OS abstractions','Abstract'),
'pearl2009causality':('Crossref book DOI 10.1017/CBO9780511803161','metadata + standard content','Sec 4.5; RW 2.6','Interventional (do-operator) / but-for framing of causation','Ch. 1, 7, 10'),
'hardy1988confused':('Crossref DOI 10.1145/54289.871709','metadata-only, used for the term confused deputy','RW 2.5','Origin of the confused deputy concept','Note (3 pages)'),
'bishop1996toctou':('author page + full-text PDF',FT,'RW 2.5','Time-of-check-to-time-of-use races','Abstract'),
'jang2014a11y':('OpenAlex DOI + full-text PDF',FT,'Intro; RW 2.5','A11y as alternative I/O path with inadequate checks; OS widgets handle real and a11y input through same channels','Abstract; Sec 3.1; Sec 5.3'),
'fratantonio2017cloak':('Crossref DOI + project page',AO,'Intro; RW 2.5','SYSTEM_ALERT_WINDOW + accessibility service gives complete control of UI feedback loop','Title; project page'),
'bianchi2015whattheapp':('OpenAlex DOI + full-text PDF',FT,'RW 2.5','UI deception attacks; trusted indicator of app origin in navigation bar','Abstract; Sec VI'),
'fernandes2016uideception':('Springer chapter + pre-proceedings PDF',FT,'RW 2.5','Attacks on secure indicator incl. TOCTOU race; defenses','Sec 4; Sec 5.2'),
'yan2019overlay':('Crossref DOI + full-text PDF',FT,'RW 2.5; Sec 5.1','Quote: programmatically visible overlay can be visually invisible to users; MobiSys 2019','Sec 3.5'),
'kalysch2018a11y':('OpenAlex DOI + lab project page',AO,'RW 2.5','A11y misuse to read other apps content','Project page summary'),
'naseri2019accessileaks':('PoPETs full-text PDF',FT,'RW 2.5','Accessibility service enables eavesdropping on app content','Abstract'),
'huang2012clickjacking':('USENIX page + full-text PDF',FT,'RW 2.5','Visual and temporal context integrity for sensitive user actions','Sec 5'),
'felt2011redelegation':('USENIX page + full-text PDF',FT,'RW 2.5','Permission re-delegation as confused deputy','Sec 1 definition'),
'android12_untrusted_touch':('developer.android.com/about/versions/12/behavior-changes-all',DOC,'RW 2.5; Sec 4.1; Sec 9','Untrusted overlay touches blocked when combined opacity >0.8; a11y, IME, assistant windows trusted','Section Untrusted touch events are blocked'),
'android15_otp_redaction':('developer.android.com/about/versions/15/behavior-changes-all',DOC,'RW 2.5; Sec 5.1; Sec 9','Untrusted NotificationListenerService cannot read unredacted OTP notifications','Section OTP Redaction'),
'android_blog_a11y_sensitive':('developer.android.com/blog/posts/enhancing-android-security-stop-malware-from-snooping-on-your-app-data',DOC,'RW 2.5; Sec 5.1; Sec 9','accessibilityDataSensitive views readable only by isAccessibilityTool services','Blog body'),
'android_accessibilityserviceinfo':('AOSP Javadoc (AccessibilityServiceInfo.java) + reference page title',DOC,'RW 2.5','isAccessibilityTool property','Method Javadoc'),
'android_accessibilitynodeinfo':('AOSP Javadoc (AccessibilityNodeInfo.java) + reference page title',DOC,'Intro; Sec 3.1; Sec 9','Node exposes package name, window id, bounds, isVisibleToUser; performAction from accessibility service','Method Javadoc'),
'android_accessibilitywindowinfo':('AOSP Javadoc (AccessibilityWindowInfo.java) + reference page title',DOC,'Intro; Sec 5.1; Sec 9','Window object exposes type, layer, id, title, focus/active, bounds; no owner','Class Javadoc; TYPE_* constants'),
'android_sdkruntime':('privacysandbox.google.com/private-advertising/sdk-runtime/architecture',DOC,'Intro; Sec 3.1; Sec 5.1','SDK Runtime runs SDKs in separate process; media rendered via SurfaceControlViewHost and embedded in app view','Sections SDKs execute in an isolated process; Media rendering'),
'android_surfaceflinger':('source.android.com/docs/core/graphics/surfaceflinger-windowmanager',DOC,'Intro; Sec 3.1; Sec 5.1','SurfaceFlinger accepts, composes, sends buffers; WindowManager oversees window lifecycle, input, focus, z-order','Page body'),
'android_appfunctions':('developer.android.com/ai/appfunctions',DOC,'RW 2.5; Sec 9','AppFunctions expose app functions to agents; Android 16+; Gemini integration private preview as of May 2026','Overview'),
'wcag21':('w3.org/TR/WCAG21',DOC,'Sec 4.1','Contrast ratio (L1+0.05)/(L2+0.05); 4.5:1 minimum for normal text','Definition of contrast ratio; SC 1.4.3'),
'sundararajan2017axiomatic':('PMLR v70 page',AO,'RW 2.6','Integrated gradients; sensitivity and implementation invariance axioms; needs gradients','Abstract'),
'abnar2020attentionflow':('ACL Anthology page',AO,'RW 2.6; Sec 5.3','Attention rollout and attention flow','Abstract'),
'jain2019attention':('ACL Anthology page',AO,'RW 2.6; Sec 5.3; Sec 7','Attention weights are not faithful explanations','Abstract'),
'greshake2023notwhat':('OpenAlex DOI record',AO,'RW 2.2','Indirect prompt injection; LLM apps blur data and instructions','Abstract'),
'zhan2024injecagent':('ACL Anthology page',AO,'RW 2.2','InjecAgent: 1,054 test cases','Abstract'),
'debenedetti2024agentdojo':('NeurIPS proceedings page',AO,'RW 2.2','AgentDojo: 97 tasks, 629 security test cases','Abstract'),
'liao2025eia':('ICLR 2025 proceedings page',AO,'RW 2.2','EIA up to 70% ASR stealing specific PII on web agents','Abstract'),
'zhang2025popups':('ACL Anthology page',AO,'RW 2.2','Pop-ups: 86% average ASR on OSWorld/VisualWebArena; basic defenses ineffective','Abstract'),
'ma2025caution':('ACL Anthology page',AO,'RW 2.2','Benign distracting content misleads multimodal GUI agents','Abstract'),
'evtimov2025wasp':('NeurIPS 2025 proceedings page',AO,'RW 2.2','WASP: end-to-end web-agent security benchmark with low-effort injections','Abstract'),
'wu2025dissecting':('ICLR 2025 page',AO,'RW 2.2','Trigger image <5% of pixels misleads multimodal agents','Abstract'),
'chen2025fineprint':('arXiv 2504.11281 full text',FT,'RW 2.2','Commands in dense legalistic text parsed indiscriminately by web agents (web, not mobile; not hidden text)','Table 1; Sec 4.1; Sec 5.1'),
'rawles2023aitw':('NeurIPS 2023 D&B page + PDF',FT,'RW 2.1','715k episodes of Android device control','Abstract'),
'rawles2025androidworld':('ICLR 2025 proceedings page',AO,'Intro; RW 2.1; Sec 8','116 programmatic tasks, 20 apps, live emulator with state checks','Abstract'),
'xu2025androidlab':('ACL Anthology page (DOI 10.18653/v1/2025.acl-long.107)',AO,'Intro; RW 2.1; Sec 8','138 tasks across nine apps; XML and SoM modes','Abstract'),
'chen2025spabench':('ICLR 2025 poster page',AO,'RW 2.1','Integrates >10 agents with resource-consumption metrics','Abstract'),
'wang2024mobileagent':('arXiv 2401.16158',AO,'RW 2.1','Vision-centric mobile agent without system-specific customization','Abstract'),
'wang2024mobileagentv2':('NeurIPS 2024 page',AO,'RW 2.1','Planning, decision, and reflection agents','Abstract'),
'ye2025mobileagentv3':('arXiv 2508.15144',AO,'Intro; RW 2.1; Sec 3; Sec 8','Mobile-Agent-v3 multi-agent framework on GUI-Owl; open source','Abstract'),
'droidrun2025software':('github.com/droidrun/mobilerun; PyPI droidrun shim; mobilerun.ai','software page verified','Intro; RW 2.1; Sec 3; Sec 8','Open-source, model-agnostic, accessibility-tree-first agent; renamed Mobilerun in 2026','README; PyPI description'),
'liu2024autoglm':('arXiv 2411.00820',AO,'Intro; RW 2.1; Sec 8','AutoGLM decouples planning and grounding via intermediate interface','Abstract'),
'openautoglm2025software':('GitHub zai-org/Open-AutoGLM','software page verified','RW 2.1; Sec 3; Sec 8','Open-AutoGLM operates from screenshots over ADB','README'),
'qin2025uitars':('arXiv 2501.12326',AO,'Intro; RW 2.1; Sec 3; Sec 8','UI-TARS native agent solely perceives screenshots','Abstract'),
'zhang2025appagent':('Crossref DOI 10.1145/3706598.3713600',AO,'RW 2.1','Learns app usage by exploration; simplified action space over annotated screenshots','Abstract'),
'wen2025autodroidv2':('Crossref DOI 10.1145/3711875.3729134',AO,'RW 2.1','On-device SLM script generation over app-documentation abstraction (MobiSys 2025)','Abstract'),
'hong2024cogagent':('CVF open access page',AO,'RW 2.1','GUI-specialized VLM from high-resolution screenshots','Abstract'),
'cheng2024seeclick':('ACL Anthology page',AO,'RW 2.1','Screenshot-only visual GUI agent; ScreenSpot','Abstract'),
'wu2025osatlas':('ICLR 2025 poster page',AO,'RW 2.1','Cross-platform GUI grounding foundation action model','Abstract'),
'zhang2025llmbrainedguiagents':('arXiv / TMLR 2025',AO,'RW 2.1','Survey organizing GUI agents by environment, perception, action','Survey sections'),
'shi2025trustworthyguiagents':('arXiv abstract',AO,'RW 2.1','Survey treating trustworthiness incl. security as a dimension','Abstract'),
'tian2026agentprog':('MobiSys 2026 page + Crossref DOI',AO,'RW 2.1','GUI agent context management with program-guided state (MobiSys 2026)','Abstract'),
'enck2010taintdroid':('USENIX OSDI full-text PDF + PSU record',FT,'RW 2.4','Dynamic taint tracking on Android at variable, method, message, file granularity with modest overhead','Abstract; Sec 1'),
'pasquier2017camflow':('Crossref DOI 10.1145/3127479.3129249 + camflow.org',MD,'RW 2.4','Whole-system kernel provenance capture (title-level statement only)','Title/abstract'),
'google2026gemininano':('developer.android.com/ai/gemini-nano',DOC,'Sec 9','Gemini Nano runs in Android AICore system service','Page body'),
}
rows=[]
for k in sorted(E):
    f=E[k]; c=C.get(k)
    if not c: print('NO CLAIM', k); continue
    venue=f.get('booktitle') or f.get('journal') or f.get('howpublished') or f.get('institution') or f.get('publisher','')
    ident=f.get('doi') and 'doi:'+f['doi'] or (f.get('eprint') and 'arXiv:'+f['eprint']) or f.get('url','')
    rows.append([k,f.get('title',''),f.get('author',''),f.get('year',''),venue,ident,c[0],c[1],c[2],c[3],c[4],''])
with open(os.path.join(root,'citation_claim_map.csv'),'w',newline='') as fh:
    w=csv.writer(fh); w.writerow(['citation_key','paper_title','authors','year','venue','DOI_or_arXiv_or_URL','verification_source','verification_level','manuscript_section','exact_claim_supported','source_location','notes'])
    w.writerows(rows)
print(len(rows),'rows')
