from django.contrib import admin
from technicalquestions_api.models import QuizQuestion, ResultTest,TimeElapsed

admin.site.register(QuizQuestion)
admin.site.register(ResultTest)
admin.site.register(TimeElapsed)