/**
 * @file mf_video_reader.cpp
 * @brief Implementation of MfVideoReader using Windows Media Foundation.
 */

#include "live_renderer/render/mf_video_reader.hpp"
#include <algorithm>
#include <cmath>

#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <mfapi.h>
#include <mfidl.h>
#include <mfreadwrite.h>
#include <propvarutil.h>

namespace live_renderer {

namespace {

void EnsureMfInitialized() {
    static bool initialized = false;
    if (!initialized) {
        CoInitializeEx(nullptr, COINIT_MULTITHREADED);
        MFStartup(MF_VERSION, MFSTARTUP_NOSOCKET);
        initialized = true;
    }
}

std::wstring Utf8ToWide(const std::string& str) {
    if (str.empty()) return L"";
    const int len = MultiByteToWideChar(
        CP_UTF8, 0, str.c_str(), static_cast<int>(str.size()), nullptr, 0);
    if (len <= 0) return L"";
    std::wstring result(len, L'\0');
    MultiByteToWideChar(
        CP_UTF8, 0, str.c_str(), static_cast<int>(str.size()), &result[0], len);
    return result;
}

}  // namespace

struct MfVideoReader::Impl {
    IMFSourceReader* reader = nullptr;
    int width = 0;
    int height = 0;
    int32_t stride = 0;
    int64_t duration_ms = 0;
    int64_t current_timestamp_ms = -1;
    int64_t next_timestamp_ms = -1;
    bool eof = false;
    std::vector<uint8_t> current_frame_rgba;

    ~Impl() {
        Close();
    }

    void Close() {
        if (reader) {
            reader->Release();
            reader = nullptr;
        }
        width = 0;
        height = 0;
        stride = 0;
        duration_ms = 0;
        current_timestamp_ms = -1;
        next_timestamp_ms = -1;
        eof = false;
        current_frame_rgba.clear();
    }

    bool ConfigureStream() {
        if (!reader) return false;
        reader->SetStreamSelection(MF_SOURCE_READER_ALL_STREAMS, FALSE);
        HRESULT hr = reader->SetStreamSelection(
            MF_SOURCE_READER_FIRST_VIDEO_STREAM, TRUE);
        if (FAILED(hr)) return false;

        IMFMediaType* media_type = nullptr;
        hr = MFCreateMediaType(&media_type);
        if (FAILED(hr) || !media_type) return false;

        media_type->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Video);
        media_type->SetGUID(MF_MT_SUBTYPE, MFVideoFormat_RGB32);
        hr = reader->SetCurrentMediaType(
            MF_SOURCE_READER_FIRST_VIDEO_STREAM, nullptr, media_type);
        media_type->Release();
        return SUCCEEDED(hr);
    }

    bool ReadMetadata() {
        if (!reader) return false;
        IMFMediaType* cur_type = nullptr;
        HRESULT hr = reader->GetCurrentMediaType(
            MF_SOURCE_READER_FIRST_VIDEO_STREAM, &cur_type);
        if (FAILED(hr) || !cur_type) return false;

        UINT32 w = 0, h = 0;
        hr = MFGetAttributeSize(cur_type, MF_MT_FRAME_SIZE, &w, &h);
        if (FAILED(hr) || w == 0 || h == 0) {
            cur_type->Release();
            return false;
        }
        width = static_cast<int>(w);
        height = static_cast<int>(h);

        INT32 default_stride = 0;
        hr = cur_type->GetUINT32(
            MF_MT_DEFAULT_STRIDE,
            reinterpret_cast<UINT32*>(&default_stride));
        if (SUCCEEDED(hr) && default_stride != 0) {
            stride = default_stride;
        } else {
            LONG calc_stride = 0;
            if (SUCCEEDED(MFGetStrideForBitmapInfoHeader(
                    MFVideoFormat_RGB32.Data1, width, &calc_stride))) {
                stride = static_cast<INT32>(calc_stride);
            } else {
                stride = static_cast<INT32>(width * 4);
            }
        }
        cur_type->Release();

        PROPVARIANT var;
        PropVariantInit(&var);
        hr = reader->GetPresentationAttribute(
            MF_SOURCE_READER_MEDIASOURCE, MF_PD_DURATION, &var);
        if (SUCCEEDED(hr)) {
            if (var.vt == VT_UI8) {
                duration_ms = static_cast<int64_t>(var.uhVal.QuadPart / 10000);
            } else if (var.vt == VT_I8) {
                duration_ms = static_cast<int64_t>(var.hVal.QuadPart / 10000);
            }
        }
        PropVariantClear(&var);
        return true;
    }

    void ConvertBgrxToRgba(const uint8_t* src, size_t src_len) {
        if (!src || width <= 0 || height <= 0) return;
        const size_t needed_bytes = static_cast<size_t>(width) * height * 4;
        if (current_frame_rgba.size() != needed_bytes) {
            current_frame_rgba.resize(needed_bytes);
        }

        const int32_t abs_stride = std::abs(stride);
        for (int y = 0; y < height; ++y) {
            size_t row_src_offset = 0;
            if (stride > 0) {
                row_src_offset = static_cast<size_t>(y) * abs_stride;
            } else {
                row_src_offset =
                    static_cast<size_t>(height - 1 - y) * abs_stride;
            }
            if (row_src_offset + static_cast<size_t>(width) * 4 > src_len) {
                break;
            }
            const uint8_t* row_src = src + row_src_offset;
            uint8_t* row_dst = current_frame_rgba.data() +
                               static_cast<size_t>(y) * (width * 4);

            for (int x = 0; x < width; ++x) {
                row_dst[x * 4 + 0] = row_src[x * 4 + 2];  // Red
                row_dst[x * 4 + 1] = row_src[x * 4 + 1];  // Green
                row_dst[x * 4 + 2] = row_src[x * 4 + 0];  // Blue
                row_dst[x * 4 + 3] = 255;                  // Alpha
            }
        }
    }

    bool ReadNextSample() {
        if (!reader) return false;
        IMFSample* sample = nullptr;
        for (int retry = 0; retry < 5; ++retry) {
            DWORD stream_idx = 0;
            DWORD flags = 0;
            LONGLONG ts_100ns = 0;
            HRESULT hr = reader->ReadSample(
                MF_SOURCE_READER_FIRST_VIDEO_STREAM,
                0,
                &stream_idx,
                &flags,
                &ts_100ns,
                &sample);

            if (FAILED(hr)) return false;
            if (flags & MF_SOURCE_READERF_ENDOFSTREAM) {
                eof = true;
                return false;
            }
            if (sample) {
                LONGLONG dur_100ns = 0;
                int64_t dur_ms = 33;
                if (SUCCEEDED(sample->GetSampleDuration(&dur_100ns)) &&
                    dur_100ns > 0) {
                    dur_ms = dur_100ns / 10000;
                }
                current_timestamp_ms = ts_100ns / 10000;
                next_timestamp_ms = current_timestamp_ms + dur_ms;
                break;
            }
        }
        if (!sample) return false;

        IMFMediaBuffer* media_buf = nullptr;
        HRESULT hr = sample->ConvertToContiguousBuffer(&media_buf);
        if (SUCCEEDED(hr) && media_buf) {
            BYTE* data_ptr = nullptr;
            DWORD max_len = 0;
            DWORD cur_len = 0;
            hr = media_buf->Lock(&data_ptr, &max_len, &cur_len);
            if (SUCCEEDED(hr) && data_ptr) {
                ConvertBgrxToRgba(data_ptr, cur_len);
                media_buf->Unlock();
            }
            media_buf->Release();
        }
        sample->Release();
        return true;
    }

    bool SeekToMs(int64_t target_ms) {
        if (!reader) return false;
        PROPVARIANT var;
        PropVariantInit(&var);
        var.vt = VT_I8;
        var.hVal.QuadPart = target_ms * 10000;
        HRESULT hr = reader->SetCurrentPosition(GUID_NULL, var);
        PropVariantClear(&var);
        if (FAILED(hr)) return false;
        eof = false;
        return ReadNextSample();
    }

    bool UpdateToTimeMs(int64_t target_ms) {
        if (!reader) return false;
        if (target_ms < current_timestamp_ms) {
            return SeekToMs(target_ms);
        }
        if (target_ms >= current_timestamp_ms &&
            target_ms < next_timestamp_ms) {
            return false;
        }
        if (target_ms - current_timestamp_ms > 1000) {
            return SeekToMs(target_ms);
        }
        bool updated = false;
        while (target_ms >= next_timestamp_ms && !eof) {
            if (!ReadNextSample()) break;
            updated = true;
        }
        if (eof && target_ms < current_timestamp_ms) {
            return SeekToMs(target_ms);
        }
        return updated;
    }
};

#else

// Non-Windows stub
namespace live_renderer {
struct MfVideoReader::Impl {
    void Close() {}
};
#endif

MfVideoReader::MfVideoReader() : impl_(std::make_unique<Impl>()) {}

MfVideoReader::~MfVideoReader() = default;

MfVideoReader::MfVideoReader(MfVideoReader&& other) noexcept = default;

MfVideoReader& MfVideoReader::operator=(
    MfVideoReader&& other) noexcept = default;

bool MfVideoReader::Open(const std::string& filepath) {
    Close();
#if defined(_WIN32)
    EnsureMfInitialized();
    std::wstring wpath = Utf8ToWide(filepath);
    if (wpath.empty()) return false;

    IMFAttributes* attributes = nullptr;
    HRESULT hr = MFCreateAttributes(&attributes, 2);
    if (SUCCEEDED(hr) && attributes) {
        attributes->SetUINT32(MF_SOURCE_READER_ENABLE_VIDEO_PROCESSING, TRUE);
        attributes->SetUINT32(MF_READWRITE_ENABLE_HARDWARE_TRANSFORMS, TRUE);
    }

    IMFSourceReader* source_reader = nullptr;
    hr = MFCreateSourceReaderFromURL(wpath.c_str(), attributes, &source_reader);
    if (attributes) attributes->Release();
    if (FAILED(hr) || !source_reader) return false;

    impl_->reader = source_reader;
    if (!impl_->ConfigureStream() || !impl_->ReadMetadata()) {
        Close();
        return false;
    }

    impl_->ReadNextSample();
    return true;
#else
    (void)filepath;
    return false;
#endif
}

void MfVideoReader::Close() {
    if (impl_) {
        impl_->Close();
    }
}

bool MfVideoReader::IsOpen() const {
#if defined(_WIN32)
    return impl_ && impl_->reader != nullptr;
#else
    return false;
#endif
}

int MfVideoReader::GetWidth() const {
#if defined(_WIN32)
    return impl_ ? impl_->width : 0;
#else
    return 0;
#endif
}

int MfVideoReader::GetHeight() const {
#if defined(_WIN32)
    return impl_ ? impl_->height : 0;
#else
    return 0;
#endif
}

int64_t MfVideoReader::GetDurationMs() const {
#if defined(_WIN32)
    return impl_ ? impl_->duration_ms : 0;
#else
    return 0;
#endif
}

int64_t MfVideoReader::GetCurrentTimestampMs() const {
#if defined(_WIN32)
    return impl_ ? impl_->current_timestamp_ms : 0;
#else
    return 0;
#endif
}

const std::vector<uint8_t>& MfVideoReader::GetCurrentFrameRgba() const {
    static const std::vector<uint8_t> kEmpty;
#if defined(_WIN32)
    return impl_ ? impl_->current_frame_rgba : kEmpty;
#else
    return kEmpty;
#endif
}

bool MfVideoReader::SeekToMs(int64_t target_ms) {
#if defined(_WIN32)
    return impl_ ? impl_->SeekToMs(target_ms) : false;
#else
    (void)target_ms;
    return false;
#endif
}

bool MfVideoReader::UpdateToTimeMs(int64_t target_ms) {
#if defined(_WIN32)
    return impl_ ? impl_->UpdateToTimeMs(target_ms) : false;
#else
    (void)target_ms;
    return false;
#endif
}

}  // namespace live_renderer

