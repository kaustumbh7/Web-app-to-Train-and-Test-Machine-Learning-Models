from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse

import os



# Create your views here.
def home(request):
    return render(request, 'deploy/index.html')


def text_classification_next(request):
    return render(request, 'deploy/text_classification_next.html')

def image_classification_next(request):
    return render(request, 'deploy/image_classification_next.html')

def upload_tc(request):
    if request.method == 'POST':
        uploaded_file = request.FILES['document']
        fs = FileSystemStorage()
        fs.save(uploaded_file.name, uploaded_file)
    return render(request, 'deploy/upload_tc.html')

def upload_ic(request):
    if request.method == 'POST':
        uploaded_file = request.FILES['document']
        fs = FileSystemStorage()
        fs.save(uploaded_file.name, uploaded_file)
    return render(request, 'deploy/upload_ic.html')

def serve_model(request):
    os.system("zip media/model.h5 media/model.zip")
    zip_file = open('media/model.zip', 'rb')
    response = HttpResponse(zip_file, content_type='application/force-download')
    #response['Content-Disposition'] = f'attachment; filename="ivr.zip"'
    response['Content-Disposition'] = 'attachment; filename="%s"' % 'model.zip'
    return response

def upload_next_ic(request):
    return render(request, 'deploy/upload_next_ic.html')

def upload_next_tc(request):
    return render(request, 'deploy/upload_next_tc.html')

def train_next_ic(request):
    token = request.POST['wandb_token']
    os.system("python deploy/image_classification/preprocess_ic.py")
    os.system("python deploy/image_classification/pytorch_classifier.py " + token)
    #print(token)
    return render(request, 'deploy/train_next.html')

def train_next_tc(request):
    token = request.POST['wandb_token']
    # Add code to train text classification model
    return render(request, 'deploy/train_next.html')