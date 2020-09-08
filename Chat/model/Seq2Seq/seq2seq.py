import os
import sys
import time
import tensorflow as tf
import model.Seq2Seq.model as model
import config.getConfig as getConfig
import io

config = {}

config = getConfig.get_config_ini('config/ini/seq2seq.ini')

vocab_inp_size = config['enc_vocab_size']
vocab_tar_size = config['dec_vocab_size']
embedding_dim = config['embedding_dim']
units = config['layer_size']
BATCH_SIZE = config['batch_size']
max_length_inp, max_length_tar = 20, 20


def preprocess_sentence(w):
    w = 'start ' + w + ' end'
    return w


def create_dataset(path, num_examples):
    lines = io.open(path, encoding='UTF-8').read().strip().split('\n')
    word_pairs = [[preprocess_sentence(w) for w in l.split('\t')] for l in lines[:num_examples]]
    return zip(*word_pairs)


def max_length(tensor):
    return max(len(t) for t in tensor)


def read_data(path, num_examples):
    input_lang, target_lang = create_dataset(path, num_examples)
    input_tensor, input_token = tokenize(input_lang)
    target_tensor, target_token = tokenize(target_lang)
    return input_tensor, input_token, target_tensor, target_token


def tokenize(lang):
    lang_tokenizer = tf.keras.preprocessing.text.Tokenizer(num_words=config['enc_vocab_size'], oov_token=3)
    lang_tokenizer.fit_on_texts(lang)

    tensor = lang_tokenizer.texts_to_sequences(lang)

    tensor = tf.keras.preprocessing.sequence.pad_sequences(tensor, maxlen=max_length_inp, padding='post')

    return tensor, lang_tokenizer


input_tensor, input_token, target_tensor, target_token = read_data(config['seq_data'], config['max_train_data_size'])


def train():
    steps_per_epoch = len(input_tensor) // config['batch_size']
    print(steps_per_epoch)
    enc_hidden = model.encoder.initialize_hidden_state()
    checkpoint_dir = config['train_data']
    ckpt = tf.io.gfile.listdir(checkpoint_dir)
    if ckpt:
        model.checkpoint.restore(tf.train.latest_checkpoint(checkpoint_dir))
    BUFFER_SIZE = len(input_tensor)
    dataset = tf.data.Dataset.from_tensor_slices((input_tensor, target_tensor)).shuffle(BUFFER_SIZE)
    dataset = dataset.batch(BATCH_SIZE, drop_remainder=True)
    checkpoint_dir = config['train_data']
    checkpoint_prefix = os.path.join(checkpoint_dir, "ckpt")
    start_time = time.time()

    while True:
        start_time_epoch = time.time()
        total_loss = 0
        for (batch, (inp, targ)) in enumerate(dataset.take(steps_per_epoch)):
            batch_loss = model.train_step(inp, targ, target_token, enc_hidden)
            total_loss += batch_loss
            print(batch_loss.numpy())

        step_time_epoch = (time.time() - start_time_epoch) / steps_per_epoch
        step_loss = total_loss / steps_per_epoch
        current_steps = +steps_per_epoch
        step_time_total = (time.time() - start_time) / current_steps
        model.checkpoint.save(file_prefix=checkpoint_prefix)
        sys.stdout.flush()


def predict(sentence):
    checkpoint_dir = config['train_data']
    model.checkpoint.restore(tf.train.latest_checkpoint(checkpoint_dir))
    sentence = preprocess_sentence(sentence)
    inputs = [input_token.word_index.get(i, 3) for i in sentence.split(' ')]
    inputs = tf.keras.preprocessing.sequence.pad_sequences([inputs], maxlen=max_length_inp, padding='post')
    inputs = tf.convert_to_tensor(inputs)

    result = ''

    hidden = [tf.zeros((1, units))]
    enc_out, enc_hidden = model.encoder(inputs, hidden)

    dec_hidden = enc_hidden
    dec_input = tf.expand_dims([target_token.word_index['start']], 0)

    for t in range(max_length_tar):
        predictions, dec_hidden, attention_weights = model.decoder(dec_input, dec_hidden, enc_out)

        predicted_id = tf.argmax(predictions[0]).numpy()

        if target_token.index_word[predicted_id] == 'end':
            break
        result += target_token.index_word[predicted_id] + ' '

        dec_input = tf.expand_dims([predicted_id], 0)

    return result
