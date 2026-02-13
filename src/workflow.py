from langgraph.graph import StateGraph
from src.agents.agent_class import MultimodalClaimVerifier
from src.fraudnet import run_fraudnet_inference, load_model, extract_clip_features, load_domain_vector, fraudnet_input
import torch
import asyncio
from typing import TypedDict, Any

# Node 1: Run stage one inference
def node_stage_1(state):
    verifier = state['verifier']
    outputs = verifier.stage_one_inference(
        state['query_image_path'],
        state['evidence_image_path'],
        state['query_caption'],
        state['txt_txt_inputs']
    )
    return {**state, 'stage1_outputs': outputs}

# # Node 2: Run colab + scoring
# def node_stage_2(state):
#     verifier = state['verifier']
#     outputs = verifier.stage_two_colab_and_scoring(state['stage1_outputs'])
#     return {**state, 'stage2_outputs': outputs}

# Node 3: Run final unified output
def node_stage_2(state):
    verifier = state['verifier']
    outputs = verifier.stage_two_colab_and_scoring(
        state['stage1_outputs'],
        state['query_image_path'],
        state['query_caption']
    )
    # breakpoint()
    return {**state, 'stage2_outputs': outputs}

# Optional: Run FraudNet as a terminal node
def node_fraudnet(state):
    fraudnet_model = state['fraudnet_model']
    # breakpoint()
    fraudnet_result = (run_fraudnet_inference(fraudnet_model, state['fraudnet_input']))
    if fraudnet_result['fraudnet_label'] == 0 : 
        fraudnet_result['confidence'] = 1 - fraudnet_result['confidence']
    return {**state, 'fraudnet_response': fraudnet_result}

class AgentState(TypedDict, total=False):
    verifier: Any
    fraudnet_model: Any
    fraudnet_input: Any
    query_image_path: str
    evidence_image_path: str
    query_caption: str
    txt_txt_inputs: list
    stage1_outputs: dict
    stage2_outputs: dict
    fraudnet_response: Any
    
# Assemble the LangGraph
def build_langgraph():
    builder = StateGraph(AgentState)

    builder.add_node("stage_1", node_stage_1)
    builder.add_node("stage_2", node_stage_2)
    # builder.add_node("stage_3", node_stage_3)
    builder.add_node("fraudnet", node_fraudnet)

    builder.set_entry_point("stage_1")
    builder.add_edge("stage_1", "stage_2")
    # builder.add_edge("stage_2", "stage_3")
    builder.add_edge("stage_2", "fraudnet")  # If needed, or set stage_3 as final if not

    return builder.compile()

# # Entry point
# if __name__ == "__main__":
#     # Inputs
#     query_image_path = '/data/image.jpg'
#     evidence_image_path = '/data/image.jpg'
#     query_caption = '''Fans Burning NTR Cutout Outside Hyderabad Theatre after the Initial Poor Ratings & Bad Talk for the Movie Devara!'''
#     txt_txt_inputs = [
#         ("Fans are burning the cutout due to poor movie reviews.", "Fans are angry at the movie Devara."),
#         ("There are negative responses on social media for Devara.", "Social media backlash against Devara.")
#     ]

#     # Load models
#     verifier = MultimodalClaimVerifier("google/gemma-3-12b-it")
#     fraudnet_model_path = "/data/shwetabh_agentic_FND/agentic_framework_1/Indian_finetuned_AL2_180_may21_iteration_4.pth.tar"
#     domain_vector_path = "/data/shwetabh_agentic_FND/agentic_framework_1/domain_vector_VITL14.json"
#     device = 'cuda:0' if torch.cuda.is_available() else 'cpu'

#     fraudnet_model = load_model(fraudnet_model_path, device=device)
#     domain_vec = load_domain_vector(domain_vector_path, device=device)

#     # Extract features
#     img_feat, text_feat = extract_clip_features(query_image_path, query_caption)
#     img_feat, text_feat = img_feat.to(device), text_feat.to(device)
#     fraudnet_inputs = fraudnet_input(
#         img_feat=img_feat.unsqueeze(0),
#         text_feat=text_feat.unsqueeze(0),
#         domain_vec=domain_vec.unsqueeze(0),
#         fake_evidence=torch.zeros(1, 20, 768).to(device)
#     )

#     # Initial state
#     state = {
#         'query_image_path': query_image_path,
#         'evidence_image_path': evidence_image_path,
#         'query_caption': query_caption,
#         'txt_txt_inputs': txt_txt_inputs,
#         'verifier': verifier,
#         'fraudnet_model': fraudnet_model,
#         'fraudnet_input': fraudnet_inputs
#     }

#     # Run the graph
#     graph = build_langgraph()
#     final_state = graph.invoke(state)
#     breakpoint()

#     # Output
#     print("\nFinal Unified Response:\n", final_state['final_output'])
#     print("\nFraudNet Response:\n", final_state['fraudnet_response'])