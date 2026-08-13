# المعمارية المخططة

> **النطاق الحالي:** توثيق تأسيسي فقط. لا توجد في Phase 1 عقد تشغيلية أو تكاملات AI أو API أو حاويات.

## الهدف المعماري

المعمارية المستقبلية تهدف إلى إنشاء سير عمل قابل للتدقيق لتحليل عقد مورد تجريبي مقابل سياسات مؤسسية تجريبية معتمدة، مع فصل المسؤوليات، وإسناد كل نتيجة إلى دليل، وإيقاف المسار الحرج لاعتماد بشري. المشروع نموذج تدريبي لدعم القرار، وليس نظامًا قانونيًا إنتاجيًا أو رأيًا قانونيًا، ولا يعتمد العقود تلقائيًا.

## نموذج الحالة المخطط

ستُمرر حالة منظمة ومتحقق منها بين العقد، بدل النص الحر، وتشمل مبدئيًا:

- معرّف تشغيل غير حساس، ومرحلة التنفيذ، والطوابع الزمنية.
- مرجع ملف تجريبي ونتيجة فحصه، دون تسجيل النص الكامل افتراضيًا.
- البنود المستخرجة ومراجع الصفحات أو المواضع.
- نسخ السياسات التجريبية المعتمدة ومعرّفاتها.
- فجوات الامتثال، والخطورة، والأدلة، ودرجة الثقة.
- قرار المراجع المستقل وأسباب النقص.
- عداد المحاولات وحدها الأقصى.
- حالة الاعتماد البشري وقرار الاستكمال.
- أحداث التدقيق ومعرّفات Traces، مع تطبيق الحجب.

سيُعرّف هذا النموذج لاحقًا باستخدام Typed schemas؛ ولم يُنفذ بعد.

## العقد (Nodes) المخططة

1. **Intake and Security Scan:** يتحقق من الملف قبل إدخال محتواه إلى المسار.
2. **Orchestrator / Planner:** ينشئ الخطة ويحدد العقدة التالية وفق الحالة.
3. **Contract Analyst:** يستخرج البنود مع مواضع الدليل.
4. **Compliance Analyst:** يقارن البنود بمصدر السياسات المعتمد فقط.
5. **Independent Reviewer:** يراجع التغطية والاتساق بصورة مستقلة.
6. **Human Approval Gate:** يوقف التشغيل للنتائج الحرجة وينتظر قرارًا صريحًا.
7. **Report Builder:** ينشئ تقريرًا محجوب البيانات وقابلًا للتدقيق.
8. **Controlled Failure:** ينهي المسار بأمان عند فشل التحقق أو نفاد المحاولات.

## المسارات الشرطية وإعادة المحاولة

التوجيه المخطط يعتمد على قيم حالة صريحة: فشل الفحص يؤدي إلى **Controlled Failure**؛ النتيجة الناقصة تعود إلى التحليل؛ النتيجة الحرجة تتجه إلى **Human Approval Gate**؛ والنتيجة المكتملة غير الحرجة تتجه إلى التقرير.

حلقة الإعادة ستكون محدودة بعداد `retry_count` وحد ثابت `max_retries`. لا يسمح أي مسار بالعودة إذا بلغ العداد الحد؛ بل ينتقل إلى فشل مضبوط وإحالة بشرية. يمنع ذلك الدوران غير المنتهي، وسيثبت اختبار منفذ مستقبلًا سلوك الحد.

## التوقف والاستكمال البشري

عند نتيجة حرجة، يُخطط لاستخدام interrupt حقيقي يحفظ checkpoint في SQLite ثم يوقف التنفيذ، لا مجرد قيمة منطقية داخل مسار مستمر. بعد قرار مراجع مخوّل، يُستأنف التشغيل من النقطة المحفوظة مع تسجيل هوية/مرجع القرار غير الحساس ووقته وسببه. لن يُنشأ التقرير النهائي الحرج قبل هذا القرار.

## الأدوات المخطط لها

- فاحص نوع PDF وحجمه وسلامته، وفاحص برمجيات خبيثة ملائم للبيئة.
- مستخرج نص وبنود مع مراجع صفحات.
- مسترجع مقيد لمستودع السياسات التجريبية المعتمدة.
- أدوات مقارنة وتصنيف وتحقق من Typed schemas.
- كاشف Prompt Injection وأداة redaction.
- أدوات tracing وmetrics وكتابة تقارير غير حساسة.

هذه أدوات مخططة؛ لا توجد استدعاءات أدوات تشغيلية في المرحلة الحالية.

## حدود الثقة

- **العقد ومنه أي نص مستخرج غير موثوق:** يعامل كبيانات فقط، ولا تُنفذ تعليماته.
- **السياسات المعتمدة:** تأتي من مخزن تجريبي مضبوط الإصدارات وقائمة سماح، ولا يجوز للعقد تعديلها أو تجاوزها.
- **الأدوات والوكلاء:** أقل صلاحية ممكنة، ومدخلاتها ومخرجاتها متحققة بنيويًا.
- **التقارير والسجلات:** تعبر حدًا يحتاج redaction؛ لا يُسجل النص الكامل للعقد دون ضرورة موثقة.
- **القرار النهائي:** يبقى داخل حد الثقة البشري، ولا يمنح للنموذج أو للعقد.

## شكل النشر المستقبلي

يُخطط لخدمة **FastAPI** تعرض نقاط إدخال وحالة وصحة مضبوطة؛ ومحرك LangGraph يدير StateGraph؛ و**SQLite** يحفظ checkpoints في النموذج التدريبي؛ و**Docker Compose** يشغّل المكونات محليًا بإعداد قابل للتكرار. ستُفصل الأسرار عبر متغيرات البيئة، وتُربط الأدلة بالـ traces. هذا الشكل غير منفذ في Phase 1 ولا يمثل جاهزية إنتاجية.

## Phase 3A implemented graph

The typed `AgentState` carries paths, structured plan, pages, clauses, policies, immutable findings, safe tool/agent events, reviewer decision and feedback, retry counters (default `max_retries=2`), route/error state, model metadata, graph path, and report paths. It contains no free-form conversation used for routing.

The executable nodes are `orchestrator`, `contract_analyst`, `compliance_analyst`, `independent_reviewer`, `report_builder`, and `controlled_failure`. Edges follow that order through review; `APPROVE` builds reports, `RETRY` returns to contract analysis while budget remains, and `FAIL` or exhaustion ends safely. The retry is a LangGraph conditional edge, not an external Python loop.

Authority is narrow: planning and tool requests are model-assisted; extraction and all findings come from Phase 2 functions; the reviewer checks completeness but cannot mutate findings. Phase 3A excludes advanced injection defenses, tracing/metrics, persistence, human interrupt/resume, API, containers, and UI.

The execution plan is authoritative rather than documentary: Pydantic requires the canonical four-tool order, each agent executes only its portion of those plan steps, and every model tool request is checked against both the role allowlist and the next planned tool. A mismatch fails closed. Reviewer input contains redacted structured finding fields, safe tool success summaries, page numbers, missing-clause state, graph path, and retry counters—never raw contract text.
