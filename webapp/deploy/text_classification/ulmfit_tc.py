from fastai.text import *
import html

import json

config = json.loads(open('deploy/text_classification/config.json').read())

BOS = 'xbos'  # beginning-of-sentence tag
FLD = 'xfld'  # data field tag

PATH=Path('')



CLAS_PATH=Path('deploy/text_classification/emotion_hindi_clas/')
CLAS_PATH.mkdir(exist_ok=True)

LM_PATH=Path('deploy/text_classification/emotion_hindi_lm/')
LM_PATH.mkdir(exist_ok=True)



CLASSES = ['angry','disappointed','excited','happy','neutral']

def get_texts(path):
    texts,labels = [],[]
    for idx,label in enumerate(CLASSES):
        for fname in (path/label).glob('*.*'):
            texts.append(fname.open('r', encoding='utf-8').read())
            labels.append(idx)
    return np.array(texts),np.array(labels)

trn_texts,trn_labels = get_texts(PATH/'train')
val_texts,val_labels = get_texts(PATH/'test')


print(len(trn_texts),len(val_texts))



col_names = ['labels','text']



np.random.seed(42)
trn_idx = np.random.permutation(len(trn_texts))
val_idx = np.random.permutation(len(val_texts))



trn_texts = trn_texts[trn_idx]
val_texts = val_texts[val_idx]

trn_labels = trn_labels[trn_idx]
val_labels = val_labels[val_idx]



df_trn = pd.DataFrame({'text':trn_texts, 'labels':trn_labels}, columns=col_names)
df_val = pd.DataFrame({'text':val_texts, 'labels':val_labels}, columns=col_names)



df_trn.to_csv(CLAS_PATH/'train_hindi.csv', header=False, index=False)
df_val.to_csv(CLAS_PATH/'test_hindi.csv', header=False, index=False)

(CLAS_PATH/'classes_hindi.txt').open('w', encoding='utf-8').writelines(f'{o}\n' for o in CLASSES)



trn_texts,val_texts = sklearn.model_selection.train_test_split(
    np.concatenate([trn_texts,val_texts]), test_size=0.1)



print(len(trn_texts), len(val_texts))



df_trn = pd.DataFrame({'text':trn_texts, 'labels':[0]*len(trn_texts)}, columns=col_names)
df_val = pd.DataFrame({'text':val_texts, 'labels':[0]*len(val_texts)}, columns=col_names)

df_trn.to_csv(LM_PATH/'train_hindi.csv', header=False, index=False)
df_val.to_csv(LM_PATH/'test_hindi.csv', header=False, index=False)



chunksize=10000



re1 = re.compile(r'  +')

def fixup(x):
    x = x.replace('#39;', "'").replace('amp;', '&').replace('#146;', "'").replace(
        'nbsp;', ' ').replace('#36;', '$').replace('\\n', "\n").replace('quot;', "'").replace(
        '<br />', "\n").replace('\\"', '"').replace('<unk>','u_n').replace(' @.@ ','.').replace(
        ' @-@ ','-').replace('\\', ' \\ ')
    return re1.sub(' ', html.unescape(x))



def get_texts(df, n_lbls=1):
    labels = df.iloc[:,range(n_lbls)].values.astype(np.int64)
    texts = f'\n{BOS} {FLD} 1 ' + df[n_lbls].astype(str)
    for i in range(n_lbls+1, len(df.columns)): texts += f' {FLD} {i-n_lbls} ' + df[i].astype(str)
    texts = list(texts.apply(fixup).values)

    tok = Tokenizer().proc_all_mp(partition_by_cores(texts))
    return tok, list(labels)



def get_all(df, n_lbls):
    tok, labels = [], []
    for i, r in enumerate(df):
        print(i)
        tok_, labels_ = get_texts(r, n_lbls)
        tok += tok_;
        labels += labels_
    return tok, labels



df_trn = pd.read_csv(LM_PATH/'train_hindi.csv', header=None, chunksize=chunksize)
df_val = pd.read_csv(LM_PATH/'test_hindi.csv', header=None, chunksize=chunksize)



tok_trn, trn_labels = get_all(df_trn, 1)
tok_val, val_labels = get_all(df_val, 1)



(LM_PATH/'tmp').mkdir(exist_ok=True)



np.save(LM_PATH/'tmp'/'tok_trn_hindi.npy', tok_trn)
np.save(LM_PATH/'tmp'/'tok_val_hindi.npy', tok_val)



tok_trn = np.load(LM_PATH/'tmp'/'tok_trn_hindi.npy')
tok_val = np.load(LM_PATH/'tmp'/'tok_val_hindi.npy')



freq = Counter(p for o in tok_trn for p in o)
#print(freq.most_common(25))



max_vocab = config['max_vocab']
min_freq = config['min_freq']



itos = [o for o,c in freq.most_common(max_vocab) if c>min_freq]
itos.insert(0, '_pad_')
itos.insert(0, '_unk_')



stoi = collections.defaultdict(lambda:0, {v:k for k,v in enumerate(itos)})
#len(itos)



trn_lm = np.array([[stoi[o] for o in p] for p in tok_trn])
val_lm = np.array([[stoi[o] for o in p] for p in tok_val])



np.save(LM_PATH/'tmp'/'trn_ids_hindi.npy', trn_lm)
np.save(LM_PATH/'tmp'/'val_ids_hindi.npy', val_lm)
pickle.dump(itos, open(LM_PATH/'tmp'/'itos_hindi.pkl', 'wb'))



trn_lm = np.load(LM_PATH/'tmp'/'trn_ids_hindi.npy')
val_lm = np.load(LM_PATH/'tmp'/'val_ids_hindi.npy')
itos = pickle.load(open(LM_PATH/'tmp'/'itos_hindi.pkl', 'rb'))



vs=len(itos)
vs,len(trn_lm)

em_sz = config['em_sz']
nh = config['nh']
nl = config['nl']


####################################################################################################################
##################################    FINE_TUNING LANGUAGE MODEL    ###############################################################
####################################################################################################################


language_model = config['language_model']
PRE_PATH = PATH/'required_files'
PRE_LM_PATH = PRE_PATH/language_model



wgts = torch.load(PRE_LM_PATH, map_location=lambda storage, loc: storage)



enc_wgts = to_np(wgts['0.encoder.weight'])
row_m = enc_wgts.mean(0)



itos2 = pickle.load((PRE_PATH/'itos_hindi.pkl').open('rb'))
itos2
stoi2 = collections.defaultdict(lambda:-1, {v:k for k,v in enumerate(itos2)})



new_w = np.zeros((vs, em_sz), dtype=np.float32)
for i,w in enumerate(itos):
    r = stoi2[w]
    new_w[i] = enc_wgts[r] if r>=0 else row_m



wgts['0.encoder.weight'] = T(new_w)
wgts['0.encoder_with_dropout.embed.weight'] = T(np.copy(new_w))
wgts['1.decoder.weight'] = T(np.copy(new_w))



wd=config['lm_wd']
bptt=config['lm_bptt']
bs=config['lm_bs']
opt_fn = partial(optim.Adam, betas=(0.8, 0.99))



trn_dl = LanguageModelLoader(np.concatenate(trn_lm), bs, bptt)
val_dl = LanguageModelLoader(np.concatenate(val_lm), bs, bptt)
md = LanguageModelData(PATH, 1,vs, trn_dl, val_dl, bs=bs, bptt=bptt)


lm_dp_list = config['lm_dp_list']
lm_dp_value= config['lm_dp_value']
drops = np.array(lm_dp_list)*lm_dp_value ################################



learner= md.get_model(opt_fn, em_sz, nh, nl, 
    dropouti=drops[0], dropout=drops[1], wdrop=drops[2], dropoute=drops[3], dropouth=drops[4])

learner.metrics = [accuracy]
learner.freeze_to(-1)
#learner2 = learner.model



learner.model.load_state_dict(wgts)



lr=config['lm_lr']
lrs = lr



learner.fit(lrs/2, 1, wds=wd, use_clr=(32,2), cycle_len=1) ##########################



learner.unfreeze()



learner.lr_find(start_lr=lrs/10, end_lr=lrs*10, linear=True)  ##########################



learner.sched.plot()

lm_unfreeze_epochs = config['lm_unfreeze_epochs']

learner.fit(lrs, 1, wds=wd, use_clr=(20,10), cycle_len=lm_unfreeze_epochs)   ##########################


fine_tuned_lm = config['fine_tuned_lm']
learner.save(fine_tuned_lm)   ##########################


fine_tuned_lm_enc = config['fine_tuned_lm_enc']
learner.save_encoder(fine_tuned_lm_enc)   ##########################





####################################################################################################################
##################################    CLASSIFIER     ###############################################################
####################################################################################################################






df_trn = pd.read_csv(CLAS_PATH/'train_hindi.csv', header=None, chunksize=chunksize)
df_val = pd.read_csv(CLAS_PATH/'test_hindi.csv', header=None, chunksize=chunksize)



tok_trn, trn_labels = get_all(df_trn, 1)
tok_val, val_labels = get_all(df_val, 1)



(CLAS_PATH/'tmp').mkdir(exist_ok=True)

np.save(CLAS_PATH/'tmp'/'tok_trn_hindi.npy', tok_trn)
np.save(CLAS_PATH/'tmp'/'tok_val_hindi.npy', tok_val)

np.save(CLAS_PATH/'tmp'/'trn_labels_hindi.npy', trn_labels)
np.save(CLAS_PATH/'tmp'/'val_labels_hindi.npy', val_labels)



tok_trn = np.load(CLAS_PATH/'tmp'/'tok_trn_hindi.npy')
tok_val = np.load(CLAS_PATH/'tmp'/'tok_val_hindi.npy')



itos = pickle.load((LM_PATH/'tmp'/'itos_hindi.pkl').open('rb'))
stoi = collections.defaultdict(lambda:0, {v:k for k,v in enumerate(itos)})
#len(itos)



trn_clas = np.array([[stoi[o] for o in p] for p in tok_trn])
val_clas = np.array([[stoi[o] for o in p] for p in tok_val])



np.save(CLAS_PATH/'tmp'/'trn_ids_hindi.npy', trn_clas)
np.save(CLAS_PATH/'tmp'/'val_ids_hindi.npy', val_clas)



trn_clas = np.load(CLAS_PATH/'tmp'/'trn_ids_hindi.npy')
val_clas = np.load(CLAS_PATH/'tmp'/'val_ids_hindi.npy')



trn_labels = np.squeeze(np.load(CLAS_PATH/'tmp'/'trn_labels_hindi.npy'))
val_labels = np.squeeze(np.load(CLAS_PATH/'tmp'/'val_labels_hindi.npy'))



#em_sz,nh,nl = 400,1150,3  ##########################
bptt = config['clas_bptt']
vs = len(itos)
opt_fn = partial(optim.Adam, betas=(0.8, 0.99))
bs = config['clas_bs']  ##########################



min_lbl = trn_labels.min()
trn_labels -= min_lbl
val_labels -= min_lbl
c=int(trn_labels.max())+1



trn_ds = TextDataset(trn_clas, trn_labels)
val_ds = TextDataset(val_clas, val_labels)
trn_samp = SortishSampler(trn_clas, key=lambda x: len(trn_clas[x]), bs=bs//2)
val_samp = SortSampler(val_clas, key=lambda x: len(val_clas[x]))
trn_dl = DataLoader(trn_ds, bs//2, transpose=True, num_workers=1, pad_idx=1, sampler=trn_samp)
val_dl = DataLoader(val_ds, bs, transpose=True, num_workers=1, pad_idx=1, sampler=val_samp)
md = ModelData(PATH, trn_dl, val_dl)


clas_dp_list = config['clas_dp_list']
clas_dp_value = config['clas_dp_list']
dps = np.array(clas_dp_list)  ##########################



dps = np.array(clas_dp_list)*clas_dp_value



m = get_rnn_classifer(bptt, 20*70, c, vs, emb_sz=em_sz, n_hid=nh, n_layers=nl, pad_token=1,
          layers=[em_sz*3, 50, c], drops=[dps[4], 0.1],
          dropouti=dps[0], wdrop=dps[1], dropoute=dps[2], dropouth=dps[3])  ##########################



opt_fn = partial(optim.Adam, betas=(0.7, 0.99))



learn = RNN_Learner(md, TextModel(to_gpu(m)), opt_fn=opt_fn)
learn.reg_fn = partial(seq2seq_reg, alpha=2, beta=1)
learn.clip=.25
learn.metrics = [accuracy]



lr=config['clas_lr'] ##########################
lrm = config['clas_lrm'] ##########################
lrs = np.array([lr/(lrm**4), lr/(lrm**3), lr/(lrm**2), lr/lrm, lr]) ##########################



lrs=np.array([1e-4,1e-4,1e-4,1e-3,1e-2])#1



wd = config['clas_wd'] ##########################
#wd = 0
learn.load_encoder(fine_tuned_lm_enc)



learn.freeze_to(-1)



learn.lr_find(lrs/1000)
learn.sched.plot()



learn.fit(lrs, 1, wds=wd, cycle_len=1, use_clr=(8,3))  ##########################



learn.freeze_to(-2)



learn.fit(lrs, 1, wds=wd, cycle_len=1, use_clr=(8,3))  ##########################



learn.unfreeze()

clas_unfreeze_epochs = config['clas_unfreeze_epochs']

learn.fit(lrs, 1, wds=wd, cycle_len=clas_unfreeze_epochs, use_clr=(32,10))  ##########################


learn.sched.plot_loss()


classification_model = config['classification_models']
learn.save(classification_model)  ##########################
