# Speed-ups for CosyVoice2 on CPU: skip the unused full-vocabulary LM head of Qwen2 on every decoding step,
# and run the flow-matching decoder under bf16 autocast (AMX).
import torch


def apply(cv, flow_bf16=True):
    enc = cv.model.llm.llm  # Qwen2Encoder

    def forward_one_step(xs, masks, cache=None):
        outs = enc.model.model(inputs_embeds=xs, attention_mask=masks[:, -1, :], use_cache=True, past_key_values=cache, return_dict=True)
        return outs.last_hidden_state, outs.past_key_values
    enc.forward_one_step = forward_one_step
    if flow_bf16:
        orig = cv.model.flow.inference

        def flow_inference(*a, **k):
            with torch.autocast('cpu', dtype=torch.bfloat16):
                out = orig(*a, **k)
            return (out[0].float(), out[1]) if isinstance(out, tuple) else out.float()
        cv.model.flow.inference = flow_inference


def llm_bf16(cv):
    """Keep the language model's weights in bf16: decoding is bound by memory traffic, so half the bytes."""
    llm = cv.model.llm
    llm.to(torch.bfloat16)
    orig = llm.inference

    def inference(*a, **k):
        with torch.autocast('cpu', dtype=torch.bfloat16):
            yield from orig(*a, **k)
    llm.inference = inference
