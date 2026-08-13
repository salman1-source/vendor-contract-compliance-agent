# مصفوفة التقييم والتتبع

الحالات المسموح بها في هذه المرحلة هي **Planned** و **In Progress** فقط.

| متطلب التقييم | التنفيذ المخطط | الدليل المطلوب | الحالة الحالية |
|---|---|---|---|
| Reasoning and tool use | خطة Plan-and-Execute واستدعاءات أدوات حقيقية بمدخلات ومخرجات منظمة | Trace منفذ يبين الخطة، والاستدعاءات، ونتائج الأدوات | Planned |
| LangGraph and state management | StateGraph بحالة Typed وتوجيه شرطي وعدّاد إعادة | اختبار مسارات وTrace للحالة والانتقالات | Planned |
| Multi-agent system | Orchestrator وContract Analyst وCompliance Analyst وIndependent Reviewer بحالة مشتركة منظمة | تشغيل منفذ يبين حدود الأدوار وتسليم الحالة والمراجعة المستقلة | Planned |
| Security guardrails | فحص ملفات، مقاومة Prompt Injection، تحقق schemas، وredaction مع fail closed | اختبارات عدائية منفذة وسجل حادث محجوب وعينة رفض | In Progress |
| Observability | Tracing وmetrics مترابطة بمعرّف تشغيل غير حساس | Trace وملف metrics محفوظان لتشغيل ناجح وفاشل | Planned |
| Persistence | SQLite checkpoint persistence لحالة قابلة للاستعادة | اختبار توقف/إعادة تشغيل يثبت استعادة النقطة | Planned |
| Human in the loop | interrupt حقيقي للنتائج الحرجة ثم resume بقرار بشري | Runtime artifact وTrace يثبتان التوقف قبل القرار والاستكمال بعده | Planned |
| Production readiness | FastAPI، فحوص صحة، Docker Compose، ضبط إعدادات وأخطاء | نتائج health check وتشغيل حاويات واختبارات API منفذة | Planned |
| Documentation and executed evidence | وثائق مرتبطة بأدلة غير حساسة وقابلة لإعادة الإنتاج | Notebook منفذ أو اختبارات وTraces وruntime artifacts محفوظة | In Progress |

## قاعدة الاكتمال

**لا يعد أي بند مكتملًا إلا إذا ارتبط باختبار منفذ أو Trace أو Notebook منفذ أو Runtime artifact محفوظ. وجود الكود وحده لا يثبت أن المسار يعمل.** لذلك لا تستخدم هذه المصفوفة حالة `Completed` قبل إنتاج الدليل الفعلي ومراجعته.
