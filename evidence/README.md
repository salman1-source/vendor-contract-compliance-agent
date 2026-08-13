# أدلة التشغيل

سيحفظ هذا المجلد مستقبلًا أدلة تشغيل **غير حساسة وقابلة لإعادة الإنتاج** تربط متطلبات التقييم بسلوك منفذ فعليًا. يجب استخدام fixtures مصطنعة، وحجب المحتوى الحساس، وتوثيق الأمر والبيئة والنتيجة اللازمة لإعادة الاختبار.

تشمل الأدلة المخططة:

- Successful end-to-end run.
- Bounded retry route.
- Controlled failure route.
- Blocked prompt-injection sample.
- Sensitive-data redaction test.
- Trace and metric artifacts.
- Stop/restart persistence.
- Human interrupt and resume.
- Docker/API health check.

**لا يُعتبر أي دليل مكتملًا قبل تنفيذ المسار فعلًا وحفظ artifact أو اختبار أو Trace قابل للمراجعة.** وجود الوثائق أو الكود وحده ليس دليل تشغيل. لا تودع العقود الحقيقية أو البيانات الشخصية أو الأسرار أو النص الكامل غير الضروري في هذا المجلد.
