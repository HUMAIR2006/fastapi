from kokoro import KModel, KPipeline
import gradio as gr
import os
import random
import torch
import logging
import datetime
import sys

# Setup logging
log_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_directory, exist_ok=True)
log_filename = os.path.join(log_directory, f'kokoro_tts_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('kokoro_tts')

# Configuration constants
IS_DUPLICATE = not os.getenv('SPACE_ID', '').startswith('c:/kuku')
CHAR_LIMIT = None if IS_DUPLICATE else 500000

# Check CUDA availability
CUDA_AVAILABLE = False
logger.info(f"CUDA available: {CUDA_AVAILABLE}")
logger.info(f"Character limit: {CHAR_LIMIT}")
logger.info(f"Is duplicate: {IS_DUPLICATE}")

# Initialize models
logger.info("Initializing models...")
models = {
    gpu: KModel(config=r'c:/kuku/Kokoro-82M/config.json', model=r'c:/kuku/Kokoro-82M/kokoro-v1_0.pth')
    .to('cpu')
    .eval()
    for gpu in [False]
}
logger.info("Models initialized successfully")

# Initialize pipelines
logger.info("Initializing pipelines...")
pipelines = {lang_code: KPipeline(lang_code=lang_code, model=False) for lang_code in 'ab'}
pipelines['a'].g2p.lexicon.golds['kokoro'] = 'kˈOkəɹO'
pipelines['b'].g2p.lexicon.golds['kokoro'] = 'kˈQkəɹQ'
logger.info("Pipelines initialized successfully")

# Model forward function for GPU
def forward_gpu(ps, ref_s, speed):
    logger.debug(f"Running forward_gpu with speed {speed}")
    return models[True](ps, ref_s, speed)

# Generate first audio segment
def generate_first(text, voice='af_heart', speed=1, use_gpu=CUDA_AVAILABLE):
    logger.info(f"Generating first audio segment for voice: {voice}, speed: {speed}, use_gpu: {use_gpu}")
    text = text if CHAR_LIMIT is None else text.strip()[:CHAR_LIMIT]
    logger.debug(f"Text length: {len(text)} characters")
    
    pipeline = pipelines[voice[0]]
    pack = pipeline.load_voice(voice)
    use_gpu = use_gpu and CUDA_AVAILABLE
    
    for _, ps, _ in pipeline(text, voice, speed):
        ref_s = pack[len(ps)-1]
        try:
            if use_gpu:
                logger.debug("Using GPU for generation")
                audio = forward_gpu(ps, ref_s, speed)
            else:
                logger.debug("Using CPU for generation")
                audio = models[False](ps, ref_s, speed)
        except gr.exceptions.Error as e:
            logger.error(f"Error during generation: {str(e)}")
            if use_gpu:
                logger.warning("GPU error, retrying with CPU")
                gr.Warning(str(e))
                gr.Info('Retrying with CPU. To avoid this error, change Hardware to CPU.')
                audio = models[False](ps, ref_s, speed)
            else:
                logger.error("CPU error, cannot continue")
                raise gr.Error(e)
        
        logger.info("Audio generation successful")
        return (24000, audio.numpy()), ps
    
    logger.warning("No audio generated")
    return None, ''

# Arena API prediction function
def predict(text, voice='af_heart', speed=1):
    logger.info(f"API prediction request for voice: {voice}, speed: {speed}")
    return generate_first(text, voice, speed, use_gpu=False)[0]

# Tokenize first text segment
def tokenize_first(text, voice='af_heart'):
    logger.info(f"Tokenizing text for voice: {voice}")
    pipeline = pipelines[voice[0]]
    for _, ps, _ in pipeline(text, voice):
        logger.debug(f"Tokenization result length: {len(ps)}")
        return ps
    
    logger.warning("No tokens generated")
    return ''

# Generate all audio segments (streaming)
def generate_all(text, voice='af_heart', speed=1, use_gpu=CUDA_AVAILABLE):
    logger.info(f"Streaming audio generation for voice: {voice}, speed: {speed}, use_gpu: {use_gpu}")
    text = text if CHAR_LIMIT is None else text.strip()[:CHAR_LIMIT]
    logger.debug(f"Text length: {len(text)} characters")
    
    pipeline = pipelines[voice[0]]
    pack = pipeline.load_voice(voice)
    use_gpu = use_gpu and CUDA_AVAILABLE
    first = True
    segment_count = 0
    
    for _, ps, _ in pipeline(text, voice, speed):
        segment_count += 1
        logger.debug(f"Generating segment {segment_count}")
        ref_s = pack[len(ps)-1]
        try:
            if use_gpu:
                logger.debug("Using GPU for streaming generation")
                audio = forward_gpu(ps, ref_s, speed)
            else:
                logger.debug("Using CPU for streaming generation")
                audio = models[False](ps, ref_s, speed)
        except gr.exceptions.Error as e:
            logger.error(f"Error during streaming generation: {str(e)}")
            if use_gpu:
                logger.warning("GPU error in streaming, switching to CPU")
                gr.Warning(str(e))
                gr.Info('Switching to CPU')
                audio = models[False](ps, ref_s, speed)
            else:
                logger.error("CPU error in streaming, cannot continue")
                raise gr.Error(e)
        
        logger.debug(f"Successfully generated segment {segment_count}")
        yield 24000, audio.numpy()
        if first:
            first = False
            logger.debug("Yielding zero buffer after first segment")
            yield 24000, torch.zeros(1).numpy()
    
    logger.info(f"Completed streaming with {segment_count} segments")

# Get random quote from file
def get_random_quote():
    logger.info("Getting random quote")
    try:
        with open(r'C:\kuku\Kokoro-TTS\en.txt', 'r') as r:
            random_quotes = [line.strip() for line in r]
        quote = random.choice(random_quotes)
        logger.debug(f"Selected random quote of length {len(quote)}")
        return quote
    except Exception as e:
        logger.error(f"Error getting random quote: {str(e)}")
        return "Error loading quote."

# Get Gatsby sample
def get_gatsby():
    logger.info("Getting Gatsby sample")
    try:
        with open(r'C:\kuku\Kokoro-TTS\gatsby5k.md', 'r') as r:
            text = r.read().strip()
        logger.debug(f"Loaded Gatsby sample of length {len(text)}")
        return text
    except Exception as e:
        logger.error(f"Error getting Gatsby sample: {str(e)}")
        return "Error loading Gatsby sample."

# Get Frankenstein sample
def get_frankenstein():
    logger.info("Getting Frankenstein sample")
    try:
        with open(r'C:\kuku\Kokoro-TTS\frankenstein5k.md', 'r') as r:
            text = r.read().strip()
        logger.debug(f"Loaded Frankenstein sample of length {len(text)}")
        return text
    except Exception as e:
        logger.error(f"Error getting Frankenstein sample: {str(e)}")
        return "Error loading Frankenstein sample."

# Voice choices dictionary
CHOICES = {
'🇺🇸 🚺 Heart ❤️': 'af_heart',
'🇺🇸 🚺 Bella 🔥': 'af_bella',
'🇺🇸 🚺 Nicole 🎧': 'af_nicole',
'🇺🇸 🚺 Aoede': 'af_aoede',
'🇺🇸 🚺 Kore': 'af_kore',
'🇺🇸 🚺 Sarah': 'af_sarah',
'🇺🇸 🚺 Nova': 'af_nova',
'🇺🇸 🚺 Sky': 'af_sky',
'🇺🇸 🚺 Alloy': 'af_alloy',
'🇺🇸 🚺 Jessica': 'af_jessica',
'🇺🇸 🚺 River': 'af_river',
'🇺🇸 🚹 Michael': 'am_michael',
'🇺🇸 🚹 Fenrir': 'am_fenrir',
'🇺🇸 🚹 Puck': 'am_puck',
'🇺🇸 🚹 Echo': 'am_echo',
'🇺🇸 🚹 Eric': 'am_eric',
'🇺🇸 🚹 Liam': 'am_liam',
'🇺🇸 🚹 Onyx': 'am_onyx',
'🇺🇸 🚹 Santa': 'am_santa',
'🇺🇸 🚹 Adam': 'am_adam',
'🇬🇧 🚺 Emma': 'bf_emma',
'🇬🇧 🚺 Isabella': 'bf_isabella',
'🇬🇧 🚺 Alice': 'bf_alice',
'🇬🇧 🚺 Lily': 'bf_lily',
'🇬🇧 🚹 George': 'bm_george',
'🇬🇧 🚹 Fable': 'bm_fable',
'🇬🇧 🚹 Lewis': 'bm_lewis',
'🇬🇧 🚹 Daniel': 'bm_daniel',
}

# Preload all voices
logger.info("Preloading all voices")
voice_count = 0
for v in CHOICES.values():
    try:
        pipelines[v[0]].load_voice(v)
        voice_count += 1
    except Exception as e:
        logger.error(f"Error preloading voice {v}: {str(e)}")
logger.info(f"Successfully preloaded {voice_count} voices")

# UI text constants
TOKEN_NOTE = '''
💡 Customize pronunciation with Markdown link syntax and /slashes/ like `[Kokoro](/kˈOkəɹO/)`

💬 To adjust intonation, try punctuation `;:,.!?—…"()""` or stress `ˈ` and `ˌ`

⬇️ Lower stress `[1 level](-1)` or `[2 levels](-2)`

⬆️ Raise stress 1 level `[or](+2)` 2 levels (only works on less stressed, usually short words)
'''

# Stream note with character limit info
STREAM_NOTE = ['⚠️ There is an unknown Gradio bug that might yield no audio the first time you click `Stream`.']
if CHAR_LIMIT is not None:
    STREAM_NOTE.append(f'✂️ Each stream is capped at {CHAR_LIMIT} characters.')
    STREAM_NOTE.append('🚀 Want more characters? You can [use Kokoro directly](https://huggingface.co/hexgrad/Kokoro-82M#usage) or duplicate this space:')
STREAM_NOTE = '\n\n'.join(STREAM_NOTE)

# Banner text
BANNER_TEXT = '''
[***Kokoro*** **is an open-weight TTS model with 82 million parameters.**](https://huggingface.co/hexgrad/Kokoro-82M)

As of January 31st, 2025, Kokoro was the most-liked [**TTS model**](https://huggingface.co/models?pipeline_tag=text-to-speech&sort=likes) and the most-liked [**TTS space**](https://huggingface.co/spaces?sort=likes&search=tts) on Hugging Face.

This demo only showcases English, but you can directly use the model to access other languages.
'''

logger.info("Setting up UI components")

# Generate tab UI
with gr.Blocks() as generate_tab:
    out_audio = gr.Audio(label='Output Audio', interactive=False, streaming=False, autoplay=True)
    generate_btn = gr.Button('Generate', variant='primary')
    with gr.Accordion('Output Tokens', open=True):
        out_ps = gr.Textbox(interactive=False, show_label=False, info='Tokens used to generate the audio, up to 510 context length.')
        tokenize_btn = gr.Button('Tokenize', variant='secondary')
        gr.Markdown(TOKEN_NOTE)
        predict_btn = gr.Button('Predict', variant='secondary', visible=False)

# Stream tab UI
with gr.Blocks() as stream_tab:
    out_stream = gr.Audio(label='Output Audio Stream', interactive=False, streaming=True, autoplay=True)
    with gr.Row():
        stream_btn = gr.Button('Stream', variant='primary')
        stop_btn = gr.Button('Stop', variant='stop')
    with gr.Accordion('Note', open=True):
        gr.Markdown(STREAM_NOTE)
        gr.DuplicateButton()

# Check API settings
API_OPEN = os.getenv('SPACE_ID') != r'c:\kuku\Kokoro-82M'
API_NAME = None if API_OPEN else False
logger.info(f"API settings: open={API_OPEN}")

# Main application UI
with gr.Blocks() as app:
    with gr.Row():
        gr.Markdown(BANNER_TEXT, container=True)
    with gr.Row():
        with gr.Column():
            text = gr.Textbox(label='Input Text', info=f"Up to ~500 characters per Generate, or {'∞' if CHAR_LIMIT is None else CHAR_LIMIT} characters per Stream")
            with gr.Row():
                voice = gr.Dropdown(list(CHOICES.items()), value='af_heart', label='Voice', info='Quality and availability vary by language')
                use_gpu = gr.Dropdown(
                    [('ZeroGPU 🚀', True), ('CPU 🐌', False)],
                    value=CUDA_AVAILABLE,
                    label='Hardware',
                    info='GPU is usually faster, but has a usage quota',
                    interactive=CUDA_AVAILABLE
                )
            speed = gr.Slider(minimum=0.5, maximum=2, value=1, step=0.1, label='Speed')
            random_btn = gr.Button('🎲 Random Quote 💬', variant='secondary')
            with gr.Row():
                gatsby_btn = gr.Button('🥂 Gatsby 📕', variant='secondary')
                frankenstein_btn = gr.Button('💀 Frankenstein 📗', variant='secondary')
        with gr.Column():
            gr.TabbedInterface([generate_tab, stream_tab], ['Generate', 'Stream'])
    
    # Connect UI elements to functions
    logger.info("Connecting UI elements to functions")
    random_btn.click(fn=get_random_quote, inputs=[], outputs=[text], api_name=API_NAME)
    gatsby_btn.click(fn=get_gatsby, inputs=[], outputs=[text], api_name=API_NAME)
    frankenstein_btn.click(fn=get_frankenstein, inputs=[], outputs=[text], api_name=API_NAME)
    generate_btn.click(fn=generate_first, inputs=[text, voice, speed, use_gpu], outputs=[out_audio, out_ps], api_name=API_NAME)
    tokenize_btn.click(fn=tokenize_first, inputs=[text, voice], outputs=[out_ps], api_name=API_NAME)
    stream_event = stream_btn.click(fn=generate_all, inputs=[text, voice, speed, use_gpu], outputs=[out_stream], api_name=API_NAME)
    stop_btn.click(fn=None, cancels=stream_event)
    predict_btn.click(fn=predict, inputs=[text, voice, speed], outputs=[out_audio], api_name=API_NAME)

# Launch the application
if __name__ == '__main__':
    logger.info("Launching application")
    try:
        app.queue(api_open=API_OPEN).launch(show_api=API_OPEN, ssr_mode=True)
        logger.info("Application started successfully")
    except Exception as e:
        logger.critical(f"Failed to start application: {str(e)}")
        raise
