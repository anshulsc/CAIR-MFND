from .prompts import (
    get_qimg_qtxt_sentiment_prompt, get_qimg_qtxt_entities_prompt, get_qimg_qtxt_event_prompt,
    get_qimg_qtxt_colab_prompt, get_response_txttxt, get_img_img_sentiment, get_img_img_unified_prompt, get_qimg_qtxt_unified_prompt, unified_prompt_v2, rationale_summary_prompt
)
from .utils import (
    load_model_and_processor, prepare_batch_inputs_from_messages, run_inference,extract_rationales, compute_weighted_support_score
)
import time

class MultimodalClaimVerifier:
    def __init__(self, model_name: str, num_prompts: int = 18, max_images_per_prompt: int = 2):
        self.model_name = model_name
        self.num_prompts = num_prompts
        self.max_images_per_prompt = max_images_per_prompt
        self.llm, self.processor = load_model_and_processor(model_name, num_prompts=num_prompts, max_images_per_prompt=max_images_per_prompt)

    def generate_inference(self, prompts, image_paths):
        batch_inputs = prepare_batch_inputs_from_messages(prompts, image_paths, self.processor)
        return run_inference(self.llm, batch_inputs)

    def stage_one_inference(self, query_image_path, evidence_image_path, query_caption, txttxt_inputs):
        # Unpack text-text inputs

        independent_prompts = [
            get_qimg_qtxt_unified_prompt(query_image_path, query_caption),
            get_img_img_unified_prompt(query_image_path, evidence_image_path)
        ]

        image_paths = [
            query_image_path,
            [query_image_path, evidence_image_path]
        ]

        # Dynamic part for arbitrary-length txttxt_inputs
        for search_result, claim in txttxt_inputs:
            independent_prompts.append(get_response_txttxt(search_result, claim))
            image_paths.append(None)

        all_generated_texts = self.generate_inference(independent_prompts, image_paths)
        return all_generated_texts

    def stage_two_colab_and_scoring(self, stage_one_outputs, query_image_path, query_caption):
        # Unpack outputs
        (
            qimg_qtxt_outputs, img_img_outputs,
            *response_txttxt_outputs  # this will be a list of responses
        ) = stage_one_outputs

        score = compute_weighted_support_score(response_txttxt_outputs)
        # support = score['support']
        # negate = score['negate']
        # final_result = 'FAKE' if support < negate else 'TRUE'
        # claim_verification_string = f"the claim is {final_result} with support score {support} and negate score {negate}."
        claim_verification_string = (f"The claim is {score['verdict']} with support score {score['score']}.")
        
        #################
        rationals=extract_rationales(response_txttxt_outputs)   #figure out how to use
        rationale_prompt = rationale_summary_prompt(rationals, query_caption)
        summary_prompt = [[
            {"role": "user", "content": [{"type": "text", "text": rationale_prompt}]}
        ]]
        rationale_summary = self.generate_inference(summary_prompt, image_paths=[None])
        #################
        
        
        unified_prompt = unified_prompt_v2(query_image=query_image_path, query_text=query_caption, 
                                        img_txt_response=qimg_qtxt_outputs, img_img_response=img_img_outputs, claim_verification_str=claim_verification_string)
        final_response = self.generate_inference([unified_prompt], [query_image_path])

        return {
            'img_txt_result' : qimg_qtxt_outputs,
            'qimg_eimg_result': img_img_outputs,
            'claim_verification_str': claim_verification_string,
            'final_response': final_response[0],
            'txt_txt_results': response_txttxt_outputs,
            'txt_txt_rational_summary': rationale_summary,
            }


    # def stage_three_final_output(self, query_image_path, query_caption, colab_outputs):

    #     v_result = colab_outputs['qimg_eimg_result']
    #     l_result = colab_outputs['qimg_qtxt_result']

    #     qimg_qtxt_sentiment = colab_outputs['qimg_qtxt_sentiment']
    #     qimg_qtxt_entities = colab_outputs['qimg_qtxt_entities']
    #     qimg_qtxt_event = colab_outputs['qimg_qtxt_event']
    #     qimg_eimg_sentiment = colab_outputs['qimg_eimg_sentiment']
    #     qimg_eimg_entities = colab_outputs['qimg_eimg_entities']
    #     qimg_eimg_event = colab_outputs['qimg_eimg_event']

    #     intermediates = colab_outputs['intermediates']
    #     static_keys = {'visual_sentiment', 'visual_entities', 'visual_event'}

    #     # Extract only the keys that came from response_txttxt_dict
    #     extracted_response_txttxt_dict = {k: v for k, v in intermediates.items() if k not in static_keys}

    #     support = colab_outputs['support_score']
    #     negate = colab_outputs['negate_score']
    #     intermediate = colab_outputs['intermediates']
    #     # Claim verification string
    #     final_result = 'FAKE' if support < negate else 'TRUE'
    #     claim_verification_str = f"the claim is {final_result} with support score {support} and negate score {negate}."
    #     breakpoint()
    #     final_prompt = unified_prompt(
    #         query_image_path,
    #         query_caption,
    #         v_result['label'], v_result['confidence'],
    #         intermediate['visual_sentiment'],
    #         intermediate['visual_entities'],
    #         intermediate['visual_event'],
    #         claim_verification_str,
    #         l_result['label'], l_result['confidence']
    #     )

    #     final_response = self.generate_inference([final_prompt], [query_image_path])
    #     final_dict = {
    #         'final_response': final_response[0],
    #         'v_result': v_result,
    #         'l_result': l_result,
    #         'claim_verification_str': claim_verification_str,
    #         'qimg_qtxt_sentiment': qimg_qtxt_sentiment,
    #         'qimg_qtxt_entities': qimg_qtxt_entities,
    #         'qimg_qtxt_event': qimg_qtxt_event,
    #         'qimg_eimg_sentiment': qimg_eimg_sentiment,
    #         'qimg_eimg_entities': qimg_eimg_entities,
    #         'qimg_eimg_event': qimg_eimg_event,
    #         **extracted_response_txttxt_dict  # dynamically unpack the keys/values here
    #     }
    #     return final_dict

if __name__ == "__main__":
    verifier = MultimodalClaimVerifier("google/gemma-3-12b-it")
    # Inputs
    query_image = "/data/shwetabh_agentic_FND/agentic_framework_1/evidence_cache/8_Sample/q_img.jpg"
    evidence_image = "/data/shwetabh_agentic_FND/agentic_framework_1/evidence_cache/8_Sample/best_evidence.jpg"
    caption = "Shreya Ghoshal has lost everything and risks going to jail"
    txttxt_inputs = [
        ("The person is holding a sign that expresses their love for AI.", "The person in the image loves AI."),
        ("The person is holding a sign that says 'I love AI'.", "The person in the image is holding a sign that says 'I love AI'.")
    ]

    start = time.time()

    # Stage 1: Initial inference
    stage1_outputs = verifier.stage_one_inference(query_image, evidence_image, caption, txttxt_inputs)
    # print("Stage 1 Response:",stage1_outputs)

    # Stage 2: Collaboration and scoring
    colab_outputs = verifier.stage_two_colab_and_scoring(stage1_outputs, query_image, caption)
    # print("Final Response:",colab_outputs)

    # # Stage 3: Final answer
    # final_response = verifier.stage_three_final_output(query_image, caption, colab_outputs)
    # print("Final Response:", final_response)

    end = time.time()
    print(f"Total time taken: {end - start:.2f} seconds")