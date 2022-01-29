import numpy as np
import scipy.sparse as sp 
import scipy.io
import copy
from scipy import pi
import sys
import pandas as pd
from os.path import join
import gzip
from scipy.io import mmwrite,mmread
from sklearn.decomposition import PCA,TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import pairwise_distances
from sklearn.cluster import KMeans
from sklearn.metrics.cluster import normalized_mutual_info_score, adjusted_rand_score
from sklearn.metrics.cluster import homogeneity_score, adjusted_mutual_info_score
from sklearn.preprocessing import MinMaxScaler,MaxAbsScaler

def compute_inertia(a, X, norm=True):
    if norm:
        W = [np.sum(pairwise_distances(X[a == c, :]))/(2.*sum(a == c)) for c in np.unique(a)]
        return np.sum(W)
    else:
        W = [np.mean(pairwise_distances(X[a == c, :])) for c in np.unique(a)]
        return np.mean(W)

#gap statistic 
def compute_gap(clustering, data, k_max=10, n_references=100):
    if len(data.shape) == 1:
        data = data.reshape(-1, 1)
    reference_inertia = []
    for k in range(2, k_max+1):
        reference = np.random.rand(*data.shape)
        mins = np.min(data,axis=0)
        maxs = np.max(data,axis=0)
        reference = reference*(maxs-mins)+mins
        local_inertia = []
        for _ in range(n_references):
            clustering.n_clusters = k
            assignments = clustering.fit_predict(reference)
            local_inertia.append(compute_inertia(assignments, reference))
        reference_inertia.append(np.mean(local_inertia))
    
    ondata_inertia = []
    for k in range(2, k_max+1):
        clustering.n_clusters = k
        assignments = clustering.fit_predict(data)
        ondata_inertia.append(compute_inertia(assignments, data))
        
    gap = np.log(reference_inertia)-np.log(ondata_inertia)
    return gap, np.log(reference_inertia), np.log(ondata_inertia)

#scRNA data
class scRNA_Sampler(object):
    def __init__(self,name,dim=20,low=0.03,has_label=True):
        self.name = name
        self.dim = dim
        self.has_label = has_label
        X = pd.read_csv('datasets/%s/sc_mat.txt'%name,sep='\t',header=0,index_col=[0]).values
        if has_label:
            labels = [item.strip() for item in open('datasets/%s/label.txt'%name).readlines()]
            uniq_labels = list(np.unique(labels))
            Y = np.array([uniq_labels.index(item) for item in labels])
            #X,Y = self.filter_cells(X,Y,min_peaks=10)
            self.Y = Y
        X = self.filter_peaks(X,low)
        #TF-IDF transformation
        nfreqs = 1.0 * X / np.tile(np.sum(X,axis=0), (X.shape[0],1))
        X  = nfreqs * np.tile(np.log(1 + 1.0 * X.shape[1] / np.sum(X,axis=1)).reshape(-1,1), (1,X.shape[1]))
        X = X.T #(cells, peaks)
        X = MinMaxScaler().fit_transform(X)
        #PCA transformation
        pca = PCA(n_components=dim, random_state=3456).fit(X)
        X = pca.transform(X)
        self.X = X
        self.total_size = self.X.shape[0]


    def filter_peaks(self,X,ratio):
        ind = np.sum(X>0,axis=1) > X.shape[1]*ratio
        return X[ind,:]

    def filter_cells(self,X,Y,min_peaks):
        ind = np.sum(X>0,axis=0) > min_peaks
        return X[:,ind], Y[ind]

    def correlation(self,X,Y,heatmap=False):
        nb_classes = len(set(Y))
        print(nb_classes)
        km = KMeans(n_clusters=nb_classes,random_state=0).fit(X)
        label_kmeans = km.labels_
        nmi = normalized_mutual_info_score(Y, label_kmeans)
        ari = adjusted_rand_score(Y, label_kmeans)
        homogeneity = homogeneity_score(Y, label_kmeans)
        ami = adjusted_mutual_info_score(Y, label_kmeans)
        print('NMI = {}, ARI = {}, Purity = {},AMI = {}, Homogeneity = {}'.format(nmi,ari,purity,ami,homogeneity))
 
    def train(self, batch_size):
        indx = np.random.randint(low = 0, high = self.total_size, size = batch_size)

        if self.has_label:
            return self.X[indx, :], self.Y[indx]
        else:
            return self.X[indx, :]

    def load_all(self):
        if self.has_label:
            return self.X, self.Y
        else:
            return self.X 


#scATAC data
class scATAC_Sampler(object):
    def __init__(self,name,dim=20,low=0.03,has_label=True):
        self.name = name
        self.dim = dim
        self.has_label = has_label
        X = pd.read_csv('datasets/%s/sc_mat.txt'%name,sep='\t',header=0,index_col=[0]).values
        if has_label:
            labels = [item.strip() for item in open('datasets/%s/label.txt'%name).readlines()]
            uniq_labels = list(np.unique(labels))
            Y = np.array([uniq_labels.index(item) for item in labels])
            #X,Y = self.filter_cells(X,Y,min_peaks=10)
            self.Y = Y
        X = self.filter_peaks(X,low)
        #TF-IDF transformation
        nfreqs = 1.0 * X / np.tile(np.sum(X,axis=0), (X.shape[0],1))
        X  = nfreqs * np.tile(np.log(1 + 1.0 * X.shape[1] / np.sum(X,axis=1)).reshape(-1,1), (1,X.shape[1]))
        X = X.T #(cells, peaks)
        X = MinMaxScaler().fit_transform(X)
        #PCA transformation
        pca = PCA(n_components=dim, random_state=3456).fit(X)
        X = pca.transform(X)
        self.X = X
        self.total_size = self.X.shape[0]


    def filter_peaks(self,X,ratio):
        ind = np.sum(X>0,axis=1) > X.shape[1]*ratio
        return X[ind,:]

    def filter_cells(self,X,Y,min_peaks):
        ind = np.sum(X>0,axis=0) > min_peaks
        return X[:,ind], Y[ind]

    def correlation(self,X,Y,heatmap=False):
        nb_classes = len(set(Y))
        print(nb_classes)
        km = KMeans(n_clusters=nb_classes,random_state=0).fit(X)
        label_kmeans = km.labels_
        nmi = normalized_mutual_info_score(Y, label_kmeans)
        ari = adjusted_rand_score(Y, label_kmeans)
        homogeneity = homogeneity_score(Y, label_kmeans)
        ami = adjusted_mutual_info_score(Y, label_kmeans)
        print('NMI = {}, ARI = {}, Purity = {},AMI = {}, Homogeneity = {}'.format(nmi,ari,purity,ami,homogeneity))
 
    def train(self, batch_size):
        indx = np.random.randint(low = 0, high = self.total_size, size = batch_size)

        if self.has_label:
            return self.X[indx, :], self.Y[indx]
        else:
            return self.X[indx, :]

    def load_all(self):
        if self.has_label:
            return self.X, self.Y
        else:
            return self.X 


#load data from 10x Genomic paired ARC technology
class Joint_Sampler(object):
    def __init__(self,name='PBMC10k',n_components=50,scale=10000,filter_feat=True,filter_cell=False,random_seed=1234,mode=1, \
        min_rna_c=0,max_rna_c=None,min_atac_c=0,max_atac_c=None):
        #c:cell, g:gene, l:locus
        self.name = name
        self.mode = mode
        self.min_rna_c = min_rna_c
        self.max_rna_c = max_rna_c
        self.min_atac_c = min_atac_c
        self.max_atac_c = max_atac_c

        self.rna_mat, self.atac_mat, self.genes, self.peaks = self.load_data(filter_feat,filter_cell)

        self.rna_mat = self.rna_mat*scale/self.rna_mat.sum(1)
        self.rna_mat = np.log10(self.rna_mat+1)
        self.atac_mat = self.atac_mat*scale/self.atac_mat.sum(1)
        self.atac_mat = np.log10(self.atac_mat+1)

        self.rna_reducer = PCA(n_components=n_components, random_state=random_seed)
        self.rna_reducer.fit(self.rna_mat)
        self.pca_rna_mat = self.rna_reducer.transform(self.rna_mat)

        self.atac_reducer = PCA(n_components=n_components, random_state=random_seed)
        self.atac_reducer.fit(self.atac_mat)
        self.pca_atac_mat = self.atac_reducer.transform(self.atac_mat)

    def load_data(self,filter_feat,filter_cell):
        mtx_file = 'datasets/%s/matrix.mtx'%self.name
        feat_file = 'datasets/%s/features.tsv'%self.name
        barcode_file = 'datasets/%s/barcodes.tsv'%self.name
        combined_mat = mmread(mtx_file).T.tocsr() #(cells, genes+peaks)
        cells = [item.strip() for item in open(barcode_file).readlines()] 
        genes = [item.split('\t')[1] for item in open(feat_file).readlines() if item.split('\t')[2]=="Gene Expression"]
        peaks = [item.split('\t')[1] for item in open(feat_file).readlines() if item.split('\t')[2]=="Peaks"]
        assert len(genes)+len(peaks) == combined_mat.shape[1]
        rna_mat = combined_mat[:,:len(genes)]
        atac_mat = combined_mat[:,len(genes):]
        print('scRNA-seq: ', rna_mat.shape, 'scATAC-seq: ', atac_mat.shape)

        if filter_feat:
            rna_mat, atac_mat, genes, peaks = self.filter_feats(rna_mat, atac_mat, genes, peaks)
            print('scRNA-seq filtered: ', rna_mat.shape, 'scATAC-seq filtered: ', atac_mat.shape)
        return rna_mat, atac_mat, genes, peaks

    def filter_feats(self, rna_mat_sp, atac_mat_sp, genes, peaks):
        #filter genes
        gene_select = np.array((rna_mat_sp>0).sum(axis=0)).squeeze() > self.min_rna_c
        if self.max_rna_c is not None:
            gene_select *= np.array((rna_mat_sp>0).sum(axis=0)).squeeze() < self.max_rna_c
        rna_mat_sp = rna_mat_sp[:,gene_select]
        genes = np.array(genes)[gene_select]
        #filter peaks
        locus_select = np.array((atac_mat_sp>0).sum(axis=0)).squeeze() > self.min_atac_c
        if self.max_atac_c is not None:
            locus_select *= np.array((atac_mat_sp>0).sum(axis=0)).squeeze() < self.max_atac_c
        atac_mat_sp = atac_mat_sp[:,locus_select]
        peaks = np.array(peaks)[locus_select]
        return rna_mat_sp, atac_mat_sp, genes, peaks

    def get_batch(self,batch_size):
        idx = np.random.randint(low = 0, high = self.atac_mat.shape[0], size = batch_size)
        if self.mode == 1:
            return self.pca_rna_mat[idx,:]
        elif self.mode == 2:
            return self.pca_atac_mat[idx,:]
        elif self.mode == 3:
            return np.hstack((self.pca_rna_mat, self.pca_atac_mat))[idx,:]
        else:
            print('Wrong mode!')
            sys.exit()
    
    def load_all(self):
        #mode: 1 only scRNA-seq, 2 only scATAC-seq, 3 both
        if self.mode == 1:
            return self.pca_rna_mat
        elif self.mode == 2:
            return self.pca_atac_mat
        elif self.mode == 3:
            return np.hstack((self.pca_rna_mat, self.pca_atac_mat))
        else:
            print('Wrong mode!')
            sys.exit()


#sample continuous (Gaussian) and discrete (Catagory) latent variables together
class Mixture_sampler(object):
    def __init__(self, nb_classes, N, dim, sd, scale=1):
        self.nb_classes = nb_classes
        self.total_size = N
        self.dim = dim
        self.sd = sd 
        self.scale = scale
        np.random.seed(1024)
        self.X_c = self.scale*np.random.normal(0, self.sd**2, (self.total_size,self.dim))
        #self.X_c = self.scale*np.random.uniform(-1, 1, (self.total_size,self.dim))
        self.label_idx = np.random.randint(low = 0 , high = self.nb_classes, size = self.total_size)
        self.X_d = np.eye(self.nb_classes)[self.label_idx]
        self.X = np.hstack((self.X_c,self.X_d))
    
    def train(self,batch_size,weights=None):
        X_batch_c = self.scale*np.random.normal(0, 1, (batch_size,self.dim))
        #X_batch_c = self.scale*np.random.uniform(-1, 1, (batch_size,self.dim))
        if weights is None:
            weights = np.ones(self.nb_classes, dtype=np.float64) / float(self.nb_classes)
        label_batch_idx =  np.random.choice(self.nb_classes, size=batch_size, replace=True, p=weights)
        X_batch_d = np.eye(self.nb_classes)[label_batch_idx]
        return X_batch_c, X_batch_d

    def load_all(self):
        return self.X_c, self.X_d

#sample continuous (Gaussian Mixture) and discrete (Catagory) latent variables together
class Mixture_sampler_v2(object):
    def __init__(self, nb_classes, N, dim, weights=None,sd=0.5):
        self.nb_classes = nb_classes
        self.total_size = N
        self.dim = dim
        np.random.seed(1024)
        if nb_classes<=dim:
            self.mean = np.random.uniform(-5,5,size =(nb_classes, dim))
            #self.mean = np.zeros((nb_classes,dim))
            #self.mean[:,:nb_classes] = np.eye(nb_classes)
        else:
            if dim==2:
                self.mean = np.array([(np.cos(2*np.pi*idx/float(self.nb_classes)),np.sin(2*np.pi*idx/float(self.nb_classes))) for idx in range(self.nb_classes)])
            else:
                self.mean = np.zeros((nb_classes,dim))
                self.mean[:,:2] = np.array([(np.cos(2*np.pi*idx/float(self.nb_classes)),np.sin(2*np.pi*idx/float(self.nb_classes))) for idx in range(self.nb_classes)])
        self.cov = [sd**2*np.eye(dim) for item in range(nb_classes)]
        if weights is None:
            weights = np.ones(self.nb_classes, dtype=np.float64) / float(self.nb_classes)
        self.Y = np.random.choice(self.nb_classes, size=N, replace=True, p=weights)
        self.X_c = np.array([np.random.multivariate_normal(mean=self.mean[i],cov=self.cov[i]) for i in self.Y],dtype='float64')
        self.X_d = np.eye(self.nb_classes)[self.Y]
        self.X = np.hstack((self.X_c,self.X_d))

    def train(self, batch_size, label = False):
        indx = np.random.randint(low = 0, high = self.total_size, size = batch_size)
        if label:
            return self.X_c[indx, :], self.X_d[indx, :], self.Y[indx, :]
        else:
            return self.X_c[indx, :], self.X_d[indx, :]

    def get_batch(self,batch_size,weights=None):
        if weights is None:
            weights = np.ones(self.nb_classes, dtype=np.float64) / float(self.nb_classes)
        label_batch_idx =  np.random.choice(self.nb_classes, size=batch_size, replace=True, p=weights)
        return self.X_c[label_batch_idx, :], self.X_d[label_batch_idx, :]
    def predict_onepoint(self,array):#return component index with max likelyhood
        from scipy.stats import multivariate_normal
        assert len(array) == self.dim
        return np.argmax([multivariate_normal.pdf(array,self.mean[idx],self.cov[idx]) for idx in range(self.nb_classes)])

    def predict_multipoints(self,arrays):
        assert arrays.shape[-1] == self.dim
        return map(self.predict_onepoint,arrays)
    def load_all(self):
        return self.X_c, self.X_d, self.label_idx

#get a batch of data from previous 50 batches, add stochastic
class DataPool(object):
    def __init__(self, maxsize=50):
        self.maxsize = maxsize
        self.nb_batch = 0
        self.pool = []

    def __call__(self, data):
        if self.nb_batch < self.maxsize:
            self.pool.append(data)
            self.nb_batch += 1
            return data
        if np.random.rand() > 0.5:
            results=[]
            for i in range(len(data)):
                idx = int(np.random.rand()*self.maxsize)
                results.append(copy.copy(self.pool[idx])[i])
                self.pool[idx][i] = data[i]
            return results
        else:
            return data