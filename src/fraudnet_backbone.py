import torch.nn as nn
import torch 
import torch.nn.functional as F
import numpy as np
from torch.autograd import Variable
from torch.nn.parameter import Parameter
import torch
from torch import nn

print_debug = False



class CoAttention(nn.Module):
    def __init__(self, d_model):
        super(CoAttention, self).__init__()
        self.query_transform = nn.Linear(d_model, d_model)
        self.key_transform = nn.Linear(d_model, d_model)

    def forward(self, image_features, text_features):    
        query = self.query_transform(image_features)
        text_features = text_features.unsqueeze(1)
        key = self.key_transform(text_features)
        # Transpose query and key
        query = query.transpose(1, 2)  # shape becomes (batch_size, 768, 22)
        key = key.transpose(1, 2)  # shape becomes (batch_size, 768, 1)
        # Compute the attention scores
        attention_scores = torch.bmm(query.transpose(1, 2), key)  # transpose query back to (batch_size, 22, 768)
        # Compute the attention weights
        attention_weights = F.softmax(attention_scores, dim=-1)
        # Compute the attended features
        attended_features = torch.bmm(attention_weights, key.transpose(1, 2))
        return attended_features



class Classifier(nn.Module):
    def __init__(self,pd):
        super(Classifier, self).__init__()
        self.cls_token_image_image = nn.Parameter(torch.randn(1, 768))
        self.cls_token_text_text = nn.Parameter(torch.randn(1, 768))
        self.cls_token_image_text = nn.Parameter(torch.randn(1, 768))
        self.cls_token_text_image = nn.Parameter(torch.randn(1, 768))
        self.sep_token = nn.Parameter(torch.randn(1, 768))
        self.cls_weight_i_i = nn.Parameter(torch.randn(1, 768))
        self.cls_weight_t_t = nn.Parameter(torch.randn(1, 768))
        self.cls_weight_i_t = nn.Parameter(torch.randn(1, 768))
        self.cls_weight_t_i = nn.Parameter(torch.randn(1, 768))
        self.co_attention = CoAttention(d_model=768)
        self.fc_joint1 = nn.Linear(3894,3894)
        self.fc_joint2 = nn.Linear(3894,3894)
        self.learn_dom_1 = nn.Linear(768,768)
        self.learn_dom_2 = nn.Linear(768,768)
        self.dom_learn_weight = Parameter(torch.Tensor(1))
        self.dom_learn_weight.data.fill_(0.9)
        self.alpha = Parameter(torch.Tensor(1))
        self.alpha.data.fill_(0.9)
        self.relu = nn.ReLU()
        self.sigmoid = nn.Sigmoid()
        self.pdrop = pd
        self.fc2 = nn.Linear(3894, 512)

        # self.bn2 = nn.BatchNorm1d(512, track_running_stats=False)
        self.bn2 = nn.BatchNorm1d(512)
        
        self.fc3 = nn.Linear(512, 64)
        
        # self.bn3 = nn.BatchNorm1d(64, track_running_stats=False)
        self.bn3 = nn.BatchNorm1d(64)
        
        self.fc4 = nn.Linear(64, 1)

        self.fc_domain_1 = nn.Linear(768,384)
        # self.bn_domain_1 = nn.BatchNorm1d(384, track_running_stats=False)
        self.bn_domain_1 = nn.BatchNorm1d(384)
        self.fc_domain_2 = nn.Linear(384,192)
        # self.bn_domain_2 = nn.BatchNorm1d(192, track_running_stats=False)
        self.bn_domain_2 = nn.BatchNorm1d(192)
        self.fc_domain_3 = nn.Linear(192,54)

        self.transf_enc_layer = nn.TransformerEncoderLayer(
                d_model=768,
                nhead=2,
                dim_feedforward=512,    #128 original
                dropout=0.1,
                activation="gelu",
                batch_first=True,
                norm_first=True,                
            )
        self.transformer = nn.TransformerEncoder(
            self.transf_enc_layer,
            num_layers=2
        )
        

    def forward(self, qimage, qtext,X_all,final_dom_vectors):
        # breakpoint()
        qimage = qimage.unsqueeze(1)
        eimg = X_all[:,:10,:]
        qtext = qtext.unsqueeze(1)
        # breakpoint()
        etext = X_all[:,10:,:]
        # breakpoint()
        text_image_features = torch.cat((qtext, eimg), dim=1)       
        image_text_features = torch.cat((qimage, etext), dim=1)

        cls_tokens_text_image = self.cls_token_text_image.repeat(qtext.shape[0], 1, 1)  # shape: (batch_size, 1, 768)
        cls_tokens_image_text = self.cls_token_image_text.repeat(qimage.shape[0], 1, 1)  # shape: (batch_size, 1, 768)

        sep_tokens = self.sep_token.repeat(qimage.shape[0], 11, 1)  # shape: (batch_size, 11, 768)

        inputs_text_image = torch.cat((cls_tokens_text_image, text_image_features, sep_tokens), dim=1)  # shape: (batch_size, 23, 768)
        inputs_image_text = torch.cat((cls_tokens_image_text, image_text_features, sep_tokens), dim=1)  # shape: (batch_size, 23, 768)
       
        output_text_image = self.transformer(inputs_text_image)
        output_image_text = self.transformer(inputs_image_text)

        cls_output_text_image = output_text_image[:, 0, :]  # shape: (batch_size, 768)
        cls_output_image_text = output_image_text[:, 0, :]  # shape: (batch_size, 768)
        
        query_text_image = output_text_image[:,1,:]
        query_image_text = output_image_text[:,1,:]
        
        # attended_t_i_i_t = self.co_attention(output_text_image[:,2:,:], query_image_text)      
        # attended_i_t_t_i = self.co_attention(output_image_text[:,2:,:], query_text_image)      
        
                
        attended_t_i_i_t = output_text_image[:,2:,:]
        attended_i_t_t_i = output_image_text[:,2:,:] 
        
        
        input_1_text_image = torch.cat((cls_output_text_image.unsqueeze(1),query_text_image.unsqueeze(1),attended_t_i_i_t), dim=1)   
        input_1_image_text = torch.cat((cls_output_image_text.unsqueeze(1),query_image_text.unsqueeze(1),attended_i_t_t_i), dim=1)      
        
        output_text_image = self.transformer(input_1_text_image)
        output_image_text = self.transformer(input_1_image_text)

        cls_output_text_image = output_text_image[:, 0, :]  # shape: (batch_size, 768)
        cls_output_image_text = output_image_text[:, 0, :]  # shape: (batch_size, 768)


        cls1 = cls_output_image_text * cls_output_text_image    
        cls2 = self.cls_weight_t_i * cls_output_text_image + self.cls_weight_i_t * cls_output_image_text    
        
        joint_features = torch.cat((cls_output_text_image.unsqueeze(1),cls_output_image_text.unsqueeze(1),cls1.unsqueeze(1),cls2.unsqueeze(1)), dim=1)
        output_joint_features = self.transformer(joint_features)
        output_joint_features = torch.cat((output_joint_features[:,0,:],output_joint_features[:,1,:],output_joint_features[:,2,:],output_joint_features[:,3,:]), dim=1)
        output_joint_features = F.dropout(output_joint_features, p=self.pdrop)

        dom = qimage*qtext
        dom = dom.squeeze()
        dom = self.fc_domain_1(dom)
        # dom = self.bn_domain_1(dom)

        # if not (self.training is False and qimage.shape[0] == 1):
        #     if not qimage.shape[0] == 1:
        #         dom = self.bn_domain_1(dom)     # For batch
        #     else:
        #         dom = self.bn_domain_1(dom.reshape(1,-1))       # Make single element into a batch of size 1
        if self.training:
            dom = self.bn_domain_1(dom)                             # 384
        else:
            if qimage.shape[0] == 1:        # Single Batch
                if print_debug:
                    print("a")
                    print(dom)
                dom = self.bn_domain_1(dom.reshape(1,-1)) 
                if print_debug:
                    print("b")
                    print(dom)                
                # m = nn.InstanceNorm2d(100)       
            else:
                dom = self.bn_domain_1(dom)        

        
        dom = self.relu(dom)
        dom = self.fc_domain_2(dom)                                 # 192
        # dom = self.bn_domain_2(dom)

        # if not (self.training is False and qimage.shape[0] == 1):
        #     if not qimage.shape[0] == 1:
        #         dom = self.bn_domain_2(dom)
        #     else:
        #         dom = self.bn_domain_2(dom.reshape(1,-1))   
        if self.training:
            dom = self.bn_domain_2(dom)
        else:
            if qimage.shape[0] == 1:        # Single Batch
                if print_debug:
                    print("c")
                    print(dom)                
                dom = self.bn_domain_2(dom.reshape(1,-1))        
                if print_debug:
                    print("d")
                    print(dom)                
            else:
                dom = self.bn_domain_2(dom)        


        # if (self.training is False and qimage.shape[0] == 1):
        #     dom = dom.unsqueeze(0)




        dom = self.relu(dom)
        dom = self.fc_domain_3(dom)

        # print("final_dom_vectors", final_dom_vectors.shape)
        # print("dom", dom.shape)
        # print("output_joint_features", output_joint_features.shape)

        joint_features = torch.cat((final_dom_vectors,dom,output_joint_features), dim=1)
        f1 =  self.fc_joint1(joint_features)
        f1 = self.relu(f1)
        f2 =  self.fc_joint2(f1)
        f3 = self.alpha * joint_features + (1-self.alpha)* f2
        joint_features = F.dropout(f3, p=self.pdrop)

        consis_out = self.fc2(joint_features) 
        #Shape here: batch_size x 512

        # consis_out = self.bn2(consis_out)
        # if not (self.training is False and qimage.shape[0] == 1):
        #     if not qimage.shape[0] == 1:        
        #         consis_out = self.bn2(consis_out)
        #     else:
        #         consis_out = self.bn2(consis_out.reshape(1,-1))
        if self.training:
            consis_out = self.bn2(consis_out)                                   #512
        else:
            if qimage.shape[0] == 1:        # Single Batch
                if print_debug:
                    print("e")
                    print(consis_out)
                consis_out = self.bn2(consis_out.reshape(1,-1))        
                if print_debug:
                    print("f")
                    print(consis_out)                
            else:   
                consis_out = self.bn2(consis_out)        

        #Shape here: batch_size x 512
        consis_out = self.relu(consis_out)
        consis_out = self.fc3(consis_out)
        
        
        # consis_out = self.bn3(consis_out)
        # if not (self.training is False and qimage.shape[0] == 1):
        #     if not qimage.shape[0] == 1:        
        #         print("a")
        #         consis_out = self.bn3(consis_out)
        #     else:
        #         print("b")
        #         consis_out = self.bn3(consis_out.reshape(1,-1))        

        # if (self.training is False and qimage.shape[0] == 1):
        #     print("c")
        #     consis_out = consis_out.unsqueeze(0)

        if self.training:
            consis_out = self.bn3(consis_out)                                   #64
        else:
            if qimage.shape[0] == 1:        # Single Batch
                if print_debug:
                    print("g")
                    print(consis_out)                
                consis_out = self.bn3(consis_out.reshape(1,-1))        
                if print_debug:
                    print("h")
                    print(consis_out)                
            else:
                consis_out = self.bn3(consis_out)
        
        
        # breakpoint()
        consis_out = self.relu(consis_out)
        consis_out = self.fc4(consis_out)

        return consis_out #,(attn_wts_t_i_1, attn_wts_i_t_1, attn_wts_t_i_2, attn_wts_i_t_2, atts_op, cls_output_text_image, cls_output_image_text)




        # if not (self.training is False and batch_size == 1):
            # batch_norm_layers go here
