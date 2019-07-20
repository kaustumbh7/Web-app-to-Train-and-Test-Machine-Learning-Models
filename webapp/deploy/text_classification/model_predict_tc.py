from fastai.text import *
from .apps import WebappConfig

def predict(sentence):
    #sentence to be classified
    idxs = np.array([[WebappConfig.stoi[p] for p in sentence.strip().split(" ")]])

    #converting sentence into numerical representation
    idxs = np.transpose(idxs)

    #get predictions from model
    p = WebappConfig.mod(VV(idxs))

    intent = str(to_np(torch.topk(p[0],1)[1])[0])
    prob = F.softmax(p[0])
    confidence = float("{0:.2f}".format(float(torch.max(prob))))  ##float(torch.max(prob))

    return(intent, confidence)

