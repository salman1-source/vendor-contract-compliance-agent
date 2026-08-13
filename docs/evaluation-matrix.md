# مصفوفة التقييم والتتبع

الحالات المسموح بها في هذه المرحلة هي **Planned** و **In Progress** فقط.

| متطلب التقييم | التنفيذ المخطط | الدليل المطلوب | الحالة الحالية |
|---|---|---|---|
| Reasoning and tool use | خطة Plan-and-Execute واستدعاءات أدوات حقيقية بمدخلات ومخرجات منظمة | Scripted-client artifacts; real-model evidence pending | In Progress |
| LangGraph and state management | StateGraph بحالة Typed وتوجيه شرطي وعدّاد إعادة | Scripted success/retry/exhaustion tests and graph export | In Progress |
| Multi-agent system | Orchestrator وContract Analyst وCompliance Analyst وIndependent Reviewer بحالة مشتركة منظمة | Scripted role evidence; real-model evidence pending | In Progress |
| Security guardrails | فحص ملفات، مقاومة Prompt Injection، تحقق schemas، وredaction مع fail closed | اختبارات عدائية منفذة وسجل حادث محجوب وعينة رفض | In Progress |
| Observability | Tracing وmetrics مترابطة بمعرّف تشغيل غير حساس | Trace وملف metrics محفوظان لتشغيل ناجح وفاشل | Planned |
| Persistence | SQLite checkpoint persistence لحالة قابلة للاستعادة | اختبار توقف/إعادة تشغيل يثبت استعادة النقطة | Planned |
| Human in the loop | interrupt حقيقي للنتائج الحرجة ثم resume بقرار بشري | Runtime artifact وTrace يثبتان التوقف قبل القرار والاستكمال بعده | Planned |
| Production readiness | FastAPI، فحوص صحة، Docker Compose، ضبط إعدادات وأخطاء | نتائج health check وتشغيل حاويات واختبارات API منفذة | Planned |
| Documentation and executed evidence | وثائق مرتبطة بأدلة غير حساسة وقابلة لإعادة الإنتاج | Notebook منفذ أو اختبارات وTraces وruntime artifacts محفوظة | In Progress |

## قاعدة الاكتمال

**لا يعد أي بند مكتملًا إلا إذا ارتبط باختبار منفذ أو Trace أو Notebook منفذ أو Runtime artifact محفوظ. وجود الكود وحده لا يثبت أن المسار يعمل.** لذلك لا تستخدم هذه المصفوفة حالة `Completed` قبل إنتاج الدليل الفعلي ومراجعته.

## Phase 2 evidence note

The deterministic Phase 2 tooling now provides Pydantic-validated inputs and outputs, real PDF/policy tool execution, fixed-rule findings, controlled CLI failures, and reproducible test/report artifacts in [`../evidence/phase2`](../evidence/phase2/). This is foundational deterministic tooling only: it does **not** satisfy or change the Planned status of reasoning agents, LangGraph, multi-agent coordination, observability, persistence, human interrupt/resume, or production deployment requirements.
