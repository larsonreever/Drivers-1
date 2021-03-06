import ctypes, os
from ctypes import c_int, c_uint8, c_uint16, c_uint32, c_char_p, c_void_p, c_long, byref
import numpy as np

import atsapi as ats

# match naming convertinos in DLL
U8 = c_uint8
U16 = c_uint16
U32 = c_uint32

# error type returned by this class
class Error(Exception):
    pass
        
class TimeoutError(Error):
    pass

# open dll
try:
    DLL = ctypes.CDLL('ATSApi32')
except:
    # if failure, try to open in driver folder
    sPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'atsapi')
    DLL = ctypes.CDLL(os.path.join(sPath, 'ATSApi32'))



class AlazarTechDigitizer():
    """Represent the Alazartech digitizer, redefines the dll functions in python"""

    def __init__(self, systemId=1, boardId=1):
        """The init case defines a session ID, used to identify the instrument"""
        # range settings; default value of 400mV for 9373; 
        #will be overwritten if model is 9870 and AlazarInputControl called
        self.dRange = {1: 0.4, 2: 0.4}
        # create a session id
        func = getattr(DLL, 'AlazarNumOfSystems')
        func.restype = U32 
        print 'Number of systems:', func()
        func = getattr(DLL, 'AlazarGetBoardBySystemID')
        func.restype = c_void_p
        handle = func(U32(systemId), U32(boardId))
        if handle is None:
            raise Error('Device with system ID=%d and board ID=%d could not be found.' % (systemId, boardId))
        self.handle = handle


    def testLED(self):
        import time
        self.callFunc('AlazarSetLED', self.handle, U32(1))
        time.sleep(0.1)
        self.callFunc('AlazarSetLED', self.handle, U32(0))


    def callFunc(self, sFunc, *args, **kargs):
        """General function caller with restype=status, also checks for errors"""
        # get function from DLL
        func = getattr(DLL, sFunc)
        func.restype = c_int
        # call function, raise error if needed
        status = func(*args)
        if 'bIgnoreError' in kargs:
            bIgnoreError = kargs['bIgnoreError']
        else:
            bIgnoreError = False
        if status>512 and not bIgnoreError:
            sError = self.getError(status)
            raise Error(sError)

    
    def getError(self, status):
        """Convert the error in status to a string"""
        func = getattr(DLL, 'AlazarErrorToText')
        func.restype = c_char_p 
        # const char* AlazarErrorToText(RETURN_CODE retCode)
        errorText = func(c_int(status))
        return str(errorText)
        
        
    def AlazarGetChannelInfo(self):
        '''Get the on-board memory in samples per channe and sample size in bits per sample'''
        memorySize_samples = U32(0)
        bitsPerSample = U8(0)
        self.callFunc('AlazarGetChannelInfo', self.handle, byref(memorySize_samples), byref(bitsPerSample))
        return (memorySize_samples, bitsPerSample)


    #RETURN_CODE AlazarSetCaptureClock( HANDLE h, U32 Source, U32 Rate, U32 Edge, U32 Decimation);
    def AlazarSetCaptureClock(self, SourceId, SampleRateId, EdgeId=0, Decimation=0):
        self.callFunc('AlazarSetCaptureClock', self.handle, 
                      U32(SourceId), U32(SampleRateId), U32(EdgeId), U32(Decimation))


    #RETURN_CODE AlazarInputControl( HANDLE h, U8 Channel, U32 Coupling, U32 InputRange, U32 Impedance);
    def AlazarInputControl(self, Channel, Coupling, InputRange, Impedance):
        # keep track of input range
        dConv = {12: 4.0, 11: 2.0, 10: 1.0, 7: 0.4, 6: 0.2, 5: 0.1, 2: 0.04}
        self.dRange[Channel] = dConv[InputRange]
        self.callFunc('AlazarInputControl', self.handle, 
                      U8(Channel), U32(Coupling), U32(InputRange), U32(Impedance))


    #RETURN_CODE AlazarSetBWLimit( HANDLE h, U8 Channel, U32 enable);
    def AlazarSetBWLimit(self, Channel, enable):
        self.callFunc('AlazarSetBWLimit', self.handle, U32(Channel), U32(enable))


    #RETURN_CODE AlazarSetTriggerOperation(HANDLE h, U32 TriggerOperation
    #            ,U32 TriggerEngine1/*j,K*/, U32 Source1, U32 Slope1, U32 Level1
    #            ,U32 TriggerEngine2/*j,K*/, U32 Source2, U32 Slope2, U32 Level2);
    def AlazarSetTriggerOperation(self, TriggerOperation=0,
                                  TriggerEngine1=0, Source1=0, Slope1=1, Level1=128,
                                  TriggerEngine2=1, Source2=3, Slope2=1, Level2=128):
        self.callFunc('AlazarSetTriggerOperation', self.handle, U32(TriggerOperation),
                      U32(TriggerEngine1), U32(Source1), U32(Slope1), U32(Level1),
                      U32(TriggerEngine2), U32(Source2), U32(Slope2), U32(Level2))


    #RETURN_CODE AlazarSetExternalTrigger( HANDLE h, U32 Coupling, U32 Range);
    def AlazarSetExternalTrigger(self, Coupling, Range=0):
        self.callFunc('AlazarSetExternalTrigger', self.handle, U32(Coupling), U32(Range))


    #RETURN_CODE  AlazarSetTriggerDelay( HANDLE h, U32 Delay);
    def AlazarSetTriggerDelay(self, Delay=0):
        self.callFunc('AlazarSetTriggerDelay', self.handle, U32(Delay))
    

    #RETURN_CODE  AlazarSetTriggerTimeOut( HANDLE h, U32 to_ns);
    def AlazarSetTriggerTimeOut(self, time=0.0):
        tick = U32(int(time*1E5))
        self.callFunc('AlazarSetTriggerTimeOut', self.handle, tick)


    #RETURN_CODE AlazarSetRecordSize( HANDLE h, U32 PreSize, U32 PostSize);
    def AlazarSetRecordSize(self, PreSize, PostSize):
        self.nPreSize = int(PreSize)
        self.nPostSize = int(PostSize)
        self.callFunc('AlazarSetRecordSize', self.handle, U32(PreSize), U32(PostSize))


    #RETURN_CODE AlazarSetRecordCount( HANDLE h, U32 Count);
    def AlazarSetRecordCount(self, Count):
        self.nRecord = int(Count)
        self.callFunc('AlazarSetRecordCount', self.handle, U32(Count))


    #RETURN_CODE AlazarStartCapture( HANDLE h);
    def AlazarStartCapture(self):
        self.callFunc('AlazarStartCapture', self.handle)


    #RETURN_CODE AlazarAbortCapture( HANDLE h);
    def AlazarAbortCapture(self):
        self.callFunc('AlazarAbortCapture', self.handle)


    #U32	AlazarBusy( HANDLE h);
    def AlazarBusy(self):
        # get function from DLL
        func = getattr(DLL, 'AlazarBusy')
        func.restype = U32
        # call function, return result
        return bool(func(self.handle))
        

    # U32	AlazarRead(HANDLE h, U32 Channel, void *buffer, int ElementSize,
    #                 long Record, long TransferOffset, U32 TransferLength);
    def AlazarRead(self, Channel, buffer, ElementSize, Record, TransferOffset, TransferLength):
        self.callFunc('AlazarRead', self.handle,
                      U32(Channel), buffer, c_int(ElementSize),
                      c_long(Record), c_long(TransferOffset), U32(TransferLength))
                      
                      
    def AlazarBeforeAsyncRead(self, channels, transferOffset, samplesPerRecord,
                        recordsPerBuffer, recordsPerAcquisition, flags):
        '''Prepares the board for an asynchronous acquisition.'''
        self.callFunc('AlazarBeforeAsyncRead', self.handle, channels, transferOffset, samplesPerRecord,
                                  recordsPerBuffer, recordsPerAcquisition, flags)
                                  
                                  
     #RETURN_CODE AlazarAbortAsyncRead( HANDLE h);                                 
    def AlazarAbortAsyncRead(self):
        '''Cancels any asynchronous acquisition running on a board.'''
        self.callFunc('AlazarAbortAsyncRead', self.handle)
        
        
    def AlazarPostAsyncBuffer(self, buffer, bufferLength):
        '''Posts a DMA buffer to a board.'''
        self.callFunc('AlazarPostAsyncBuffer', self.handle, buffer, bufferLength)
        
        
    def AlazarWaitAsyncBufferComplete(self, buffer, timeout_ms):
        '''Blocks until the board confirms that buffer is filled with data.'''
        self.callFunc('AlazarWaitAsyncBufferComplete', self.handle, buffer, timeout_ms)


    def readTracesDMA(self, Channel1, Channel2):
        """read traces in NPT AutoDMA mode, convert to float, average to single trace"""
        #Select the number of pre-trigger samples...not supported in NPT, keeping for consistency
        preTriggerSamplesValue = 0
        #change alignment to be 128
        if preTriggerSamplesValue > 0:
            preTriggerSamples = (preTriggerSamplesValue // 128  + 1)*128
        else:
            preTriggerSamples = 0
        
        #Select the number of samples per record.
        postTriggerSamplesValue = self.nPostSize
        #change alignment to be 128
        postTriggerSamples = (postTriggerSamplesValue // 128  + 1)*128
        
        samplesPerRecordValue = preTriggerSamplesValue + postTriggerSamplesValue
        
        #Select the number of records per DMA buffer.
        recordsPerBuffer = self.nRecord
    
        # TODO: Select the number of buffers per acquisition.
        buffersPerAcquisition = 1
        #Select the active channels.
        channels = Channel1 | Channel2
        channelCount = 0
        for c in ats.channels:
            channelCount += (c & channels == c)

    
        # Compute the number of bytes per record and per buffer
        memorySize_samples, bitsPerSample = self.AlazarGetChannelInfo()
        bytesPerSample = (bitsPerSample.value + 7) // 8
        samplesPerRecord = preTriggerSamples + postTriggerSamples
        bytesPerRecord = bytesPerSample * samplesPerRecord
        bytesPerBuffer = bytesPerRecord * recordsPerBuffer * channelCount
    
        # TODO: Select number of DMA buffers to allocate
        bufferCount = 1
    
        # Allocate DMA buffers
    
        sample_type = ctypes.c_uint8
        if bytesPerSample > 1:
            sample_type = ctypes.c_uint16
    
        buffers = []
        for i in range(bufferCount):
            buffers.append(ats.DMABuffer(sample_type, bytesPerBuffer))
        
        # Set the record size
        self.AlazarSetRecordSize(preTriggerSamples, postTriggerSamples)
    
        recordsPerAcquisition = recordsPerBuffer * buffersPerAcquisition
    
        # Configure the board to make a Traditional AutoDMA acquisition
        self.AlazarBeforeAsyncRead(channels,
                              -preTriggerSamples,
                              samplesPerRecord,
                              recordsPerBuffer,
                              recordsPerAcquisition,
                              ats.ADMA_EXTERNAL_STARTCAPTURE | ats.ADMA_NPT)

    
        # Post DMA buffers to board
        for buffer in buffers:
            self.AlazarPostAsyncBuffer(buffer.addr, buffer.size_bytes)
    
        try:
            self.AlazarStartCapture() # Start the acquisition
            buffersCompleted = 0
            bytesTransferred = 0
            #initialize data array
            #vData = np.zeros(channelCount*samplesPerRecord, dtype=float)
            vData = [np.zeros(samplesPerRecord, dtype=float), np.zeros(samplesPerRecord, dtype=float)]
            #range and zero for conversion to voltages
            codeZero = 2 ** (float(bitsPerSample.value) - 1) - 0.5
            codeRange = 2 ** (float(bitsPerSample.value) - 1) - 0.5 
            while (buffersCompleted < buffersPerAcquisition):
                # Wait for the buffer at the head of the list of available
                # buffers to be filled by the board.
                buffer = buffers[buffersCompleted % len(buffers)]
                self.AlazarWaitAsyncBufferComplete(buffer.addr, timeout_ms=5000)
                buffersCompleted += 1
                bytesTransferred += buffer.size_bytes
    
                # TODO: Process sample data in this buffer. Data is available
                # as a NumPy array at buffer.buffer
                vBuffer = buffer.buffer
                vBuffer16 = (vBuffer/16 - codeZero)

                for i in range(recordsPerBuffer):
                    if channels == 1:
                        vData[0] += self.dRange[1]/codeRange * vBuffer16[i*samplesPerRecord:(i+1)*samplesPerRecord]
                        #vData[1] += np.zeros(samplesPerRecord, dtype=float)
                    elif channels == 2:
                        #vData[0] += np.zeros(samplesPerRecord, dtype=float)
                        vData[1] += self.dRange[2]/codeRange * vBuffer16[i*samplesPerRecord:(i+1)*samplesPerRecord]
                    elif channels == 3:
                        #despite not setting the flag, samples seem interleaved...
                        vData[0] += self.dRange[1]/codeRange * vBuffer16[2*i*samplesPerRecord:2*(i+1)*samplesPerRecord:2]
                        vData[1] += self.dRange[2]/codeRange * vBuffer16[(2*i*samplesPerRecord+1):(2*(i+1)*samplesPerRecord+1):2]
                        
                #
                # Sample codes are unsigned by default. As a result:
                # - 0x00 represents a negative full scale input signal.
                # - 0x80 represents a ~0V signal.
                # - 0xFF represents a positive full scale input signal.
    
                # Add the buffer to the end of the list of available buffers.
                self.AlazarPostAsyncBuffer(buffer.addr, buffer.size_bytes)
        finally:
            self.AlazarAbortAsyncRead()
        #normalize        
        vData[0] /= self.nRecord
        vData[1] /= self.nRecord
        #return data - requested vector length, not restricted to 128 multiple
        return vData[0][:samplesPerRecordValue], vData[1][:samplesPerRecordValue]
    
    def readTraces(self, Channel):
        """Read traces, convert to float, average to a single trace"""
        # define sizes
        bitsPerSample = 8
        bytesPerSample = int(np.floor((float(bitsPerSample) + 7.) / 8.0))
        #TODO: change so buffer alignment is 64!!
        samplesPerRecord = self.nPreSize + self.nPostSize
        # The buffer must be at least 16 samples larger than the transfer size
        samplesPerBuffer = samplesPerRecord + 16
        dataBuffer = (c_uint8*samplesPerBuffer)()
        # define scale factors
        codeZero = 2 ** (float(bitsPerSample) - 1) - 0.5
        codeRange = 2 ** (float(bitsPerSample) - 1) - 0.5
        voltScale = self.dRange[Channel] /codeRange
        # initialize a scaled float vector
        vData = np.zeros(samplesPerRecord, dtype=float)
        for n1 in range(self.nRecord):
            self.AlazarRead(Channel, dataBuffer, bytesPerSample, n1+1,
                            -self.nPreSize, samplesPerRecord)
            # convert and scale to float
            vBuffer = voltScale * ((np.array(dataBuffer[:samplesPerRecord]) - codeZero))
            # add to output vector
            vData += vBuffer
        # normalize
        vData /= self.nRecord
        return vData



if __name__ == '__main__':
    #
#    descriptor = AqDataDescriptor()
#    for s in descriptor._fields_:
#        print s[0], getattr(descriptor, s[0])
    
    # test driver
    Digitizer = AlazarTechDigitizer()


    


