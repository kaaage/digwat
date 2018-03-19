import wave
import struct
import sys

###
# Uses LSB hiding to embed a given set of watermark data into a specified cover .wav audio file
#
# Parameters:
# - cover_work        is the path to a host WAV audio file 
# - payload           is the data to be embedded (can be any type, only the binary representation is used)
# - watermarked_work  is the path for the watermarked audio data to be written to
###
def lsb_embed(cover_work, payload, watermarked_work):
    
    payload_str = str(payload)
    watermark = struct.unpack("%dB" % len(payload_str), payload_str)
    
    w_size = len(watermark)
    w_bits = payload_to_bits((w_size,), 32)
    w_bits.extend(payload_to_bits(watermark))
    
    cover_audio = wave.open(cover_work, 'rb') 
    
    (nchannels, sampwidth, framerate, nframes, comptype, compname) = cover_audio.getparams()
    frames = cover_audio.readframes (nframes * nchannels)
    samples = struct.unpack_from ("%dh" % nframes * nchannels, frames)

    if len(samples) < len(w_bits):
        raise OverflowError("The payload data (%d bits) is too big for the cover audio (%d bits)!" % (len(w_bits), len(samples))) 
    
    print "Embedding %d bits in %s (%d samples)" % (len(w_bits), cover_work, len(samples))
    
    encoded_samples = []
    
    w_position = 0
    n = 0
    for sample in samples:
        encoded_sample = sample
        
        if w_position < len(w_bits):
            encode_bit = w_bits[w_position]
            if encode_bit == 1:
                encoded_sample = sample | encode_bit
            else:
                encoded_sample = sample
                if sample & 1 != 0:
                    encoded_sample = sample - 1
                    
            w_position = w_position + 1
            
        encoded_samples.append(encoded_sample)
            
    encoded_audio = wave.open(watermarked_work, 'wb')
    encoded_audio.setparams( (nchannels, sampwidth, framerate, nframes, comptype, compname) )

    encoded_audio.writeframes(struct.pack("%dh" % len(encoded_samples), *encoded_samples))

def payload_to_bits(watermark, nbits=8):
    w_bits = []
    for byte in watermark:
        for i in range(0,nbits):
            w_bits.append( (byte & (2 ** i)) >> i )
    return w_bits
    
def recover_embedded(watermarked_filepath):
    # Simply collect the LSB from each sample
    watermarked_audio = wave.open(watermarked_filepath, 'rb') 
    
    (nchannels, sampwidth, framerate, nframes, comptype, compname) = watermarked_audio.getparams()
    frames = watermarked_audio.readframes (nframes * nchannels)
    samples = struct.unpack_from ("%dh" % nframes * nchannels, frames)
    
    # determine how many watermark bytes we should look for
    w_bytes = 0
    for (sample,i) in zip(samples[0:32], range(0,32)):
        w_bytes = w_bytes + ( (sample & 1) * (2 ** i))
    
    print "Recovering %d bytes of payload data from %s (%d samples)" % (w_bytes, watermarked_filepath, len(samples))
    
    payload = []
    
    for n in range(0, w_bytes):
        w_byte_samples = samples[32 + (n * 8) : 32+((n+1) * 8)]
        w_byte = 0
        for (sample, i) in zip(w_byte_samples, range(0,8)):
            w_byte = w_byte + ( (sample & 1) * (2**i) )
        payload.append(w_byte)
            
    return payload
    
def watermark_to_string(list):
    return "".join([chr(x) for x in list])

if __name__ == "__main__":
    message = ""
    cover_audio = ""
    output = ""

    if len(sys.argv) > 1:
        message = sys.argv[1]
        if len(sys.argv) > 2:
            cover_audio = sys.argv[2]
            if len(sys.argv) > 3:
                output = sys.argv[3]
    if len(message) == 0 or len(cover_audio) == 0 or len(output) == 0:
        print "Wrong parameters. Example: \"python lsb.py 'This is a hidden message.' cover_audio.wav watermarked_audio.wav\""
        exit(1)
    lsb_embed(cover_audio, message, output)
    
    recover_embedded(output)
