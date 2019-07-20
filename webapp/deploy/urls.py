from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('tc_next', views.text_classification_next, name='tc_next'),
    path('ic_next', views.image_classification_next, name='ic_next'),
    path('upload_tc', views.upload_tc, name='upload_tc'),
    path('upload_ic', views.upload_ic, name='upload_ic'),
    path('upload_next_tc', views.upload_next_tc, name='upload_next_tc'),
    path('upload_next_ic', views.upload_next_ic, name='upload_next_ic'),
    path('train_next_ic', views.train_next_ic, name='train_next_ic'),
    path('train_next_tc', views.train_next_tc, name='train_next_tc'),
    path('download', views.serve_model, name='serve_model')
]