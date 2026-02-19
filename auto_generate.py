import os
import sys
import json
import time
from http import HTTPStatus
import argparse
from datetime import datetime

try:
    import requests
except Exception:
    print("requests is required. Please install via: pip install requests")
    raise

try:
    import dashscope
    from dashscope import ImageSynthesis, MultiModalConversation
    HAS_DASHSCOPE = True
except Exception:
    HAS_DASHSCOPE = False

DEFAULT_OUTPUT_DIR = 'output/generated'
LOG_FILE = 'generated_image_url.txt'

INPUT_DEFAULT = 'models_to_use.json'


def parse_date(s):
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    # fallback try ISO
    try:
        return datetime.fromisoformat(s)
    except Exception:
        raise ValueError(f"Unrecognized date format: {s}")


def parse_remaining_str(s):
    """Parse remaining string like '86/100' or '无免费额度' -> remaining int (0 if none)."""
    if not s:
        return 0
    s = str(s).strip()
    if s == '-' or '无' in s or s.lower().startswith('no'):
        return 0
    try:
        if '/' in s:
            parts = s.split('/')
            return int(parts[0])
        return int(s)
    except Exception:
        return 0


def format_remaining_str(remaining, original=None):
    """Format remaining back to string; try to preserve total from original like '86/100'."""
    try:
        if original and isinstance(original, str) and '/' in original:
            total = original.split('/')[1]
            return f"{remaining}/{total}"
    except Exception:
        pass
    return str(remaining)


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def download_and_save(url, dest_dir, prefix):
    try:
        r = requests.get(url, stream=True, timeout=60)
        if r.status_code == 200:
            ct = r.headers.get('content-type','')
            ext = '.jpg'
            if 'png' in ct:
                ext = '.png'
            elif 'mp4' in ct or 'video' in ct:
                ext = '.mp4'
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            fname = f"{prefix}_{ts}{ext}"
            path = os.path.join(dest_dir, fname)
            with open(path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            return path
        else:
            print(f"Download failed: {r.status_code} from {url}")
    except Exception as e:
        print(f"Download exception: {e}")
    return None


def call_http(endpoint, api_key, prompt, size, model=None, messages=None):
    if messages:
        payload = {
            "model": model or "",
            "input": {
                "messages": messages
            },
            "parameters": {"prompt_extend": False, "size": size}
        }
    else:
        payload = {
            "model": model or "",
            "input": {
                "messages": [
                    {"role": "user", "content": [{"text": prompt}]}
                ]
            },
            "parameters": {"prompt_extend": False, "size": size}
        }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    r = requests.post(endpoint, json=payload, headers=headers, timeout=120)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, r.text


def call_http_video(endpoint, api_key, payload, async_enable=True, timeout=120):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    if async_enable:
        headers['X-DashScope-Async'] = 'enable'
    r = requests.post(endpoint, json=payload, headers=headers, timeout=timeout)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, r.text


def poll_video_result(task_id, api_key, region='cn', poll_interval=15, max_wait=600):
    """Poll the task query endpoint for a given task_id until completed.

    region: 'cn' -> dashscope.aliyuncs.com (北京)
            'sg' -> dashscope-intl.aliyuncs.com (新加坡)
            'us' -> dashscope-us.aliyuncs.com (弗吉尼亚)
    Returns (status_code, data) where data contains 'video_urls' on success.
    """
    host_map = {
        'cn': 'dashscope.aliyuncs.com',
        'sg': 'dashscope-intl.aliyuncs.com',
        'us': 'dashscope-us.aliyuncs.com'
    }
    host = host_map.get(region, host_map['cn'])
    task_url = f"https://{host}/api/v1/tasks/{task_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    elapsed = 0
    while elapsed < max_wait:
        try:
            r = requests.get(task_url, headers=headers, timeout=60)
            try:
                data = r.json()
            except Exception:
                data = None

            if r.status_code in (200, HTTPStatus.OK) and isinstance(data, dict):
                status = data.get('status') or data.get('task_status') or data.get('state')
                if status and status.upper() in ('SUCCEEDED', 'SUCCEEDED'.lower()):
                    # extract video urls
                    output = data.get('output', {})
                    results_out = output.get('results', []) or output.get('choices', []) or []
                    video_urls = []
                    for item in results_out:
                        if isinstance(item, dict):
                            if 'video' in item:
                                video_urls.append(item['video'])
                            elif 'url' in item:
                                video_urls.append(item['url'])
                            elif 'message' in item and isinstance(item['message'], dict):
                                content = item['message'].get('content', [])
                                for it in content:
                                    if isinstance(it, dict) and ('video' in it or 'url' in it):
                                        video_urls.append(it.get('video') or it.get('url'))
                    if video_urls:
                        return 200, {'video_urls': video_urls}
                elif status and status.upper() in ('FAILED', 'ERROR'):
                    return 400, {'error': 'task failed', 'detail': data}
                # else still pending/running, continue polling
            # fallback: if r returned video links directly
            if r.status_code in (200, HTTPStatus.OK) and isinstance(data, dict):
                output = data.get('output', {})
                results_out = output.get('results', []) or output.get('choices', []) or []
                for item in results_out:
                    if isinstance(item, dict) and ('video' in item or 'url' in item):
                        return 200, {'video_urls': [item.get('video') or item.get('url')]}
        except Exception:
            pass
        time.sleep(poll_interval)
        elapsed += poll_interval

    return 202, {'error': 'timeout waiting for video result', 'request_id': task_id}


def call_sdk_image(model, prompt, size, api_key, messages=None, n=1, watermark=False, negative_prompt=None, prompt_extend=False):
    if not HAS_DASHSCOPE:
        raise RuntimeError('dashscope SDK not available')
    dashscope.api_key = api_key
    # If messages provided, use MultiModalConversation for richer multimodal calls
    if messages:
        call_kwargs = {
            'api_key': api_key,
            'model': model,
            'messages': messages,
            'result_format': 'message',
            'stream': False,
            'n': n
        }
        if watermark is not None:
            call_kwargs['watermark'] = watermark
        if negative_prompt:
            call_kwargs['negative_prompt'] = negative_prompt
        return MultiModalConversation.call(**call_kwargs)
    # Fallback to ImageSynthesis for simple prompts
    return ImageSynthesis.call(model=model, prompt=prompt, size=size, n=n, quality='standard')


def process_entries(entries, api_key, dest_dir, default_prompt=None, default_size='1024*1024', model_type='generation', max_entries=None, input_file=None, prompt_json=None):
    ensure_dir(dest_dir)
    results = []
    now = datetime.now()
    # filter and sort by expiry, skip entries without expires date
    # optionally filter by type (generation or edit)
    valid_entries = [e for e in entries if e.get('expires') and e['expires'].strip()]
    if model_type in ['generation', 'edit']:
        valid_entries = [e for e in valid_entries if e.get('type', 'generation') == model_type]
    entries_sorted = sorted(valid_entries, key=lambda e: parse_date(e['expires']))
    if isinstance(max_entries, int) and max_entries > 0:
        entries_sorted = entries_sorted[:max_entries]

    for entry in entries_sorted:
        name = entry.get('name') or entry.get('model') or 'model'
        expires = parse_date(entry['expires'])
        if expires < now:
            print(f"Skipping expired: {name} (expired {expires})")
            continue
        # check remaining quota
        rem_str = entry.get('remaining','')
        rem = parse_remaining_str(rem_str)
        if rem <= 0:
            print(f"Skipping {name}: no remaining quota ({rem_str})")
            continue
        print(f"Using: {name}, expires: {expires}")
        prompt = entry.get('prompt') or default_prompt or '生成一张图片'
        size = entry.get('size') or default_size
        method = entry.get('method','http')
        endpoint = entry.get('url')
        model = entry.get('model')

        image_urls = []
        
        # Determine HTTP messages: use structured JSON if provided
        http_messages = None
        if prompt_json is not None:
            if isinstance(prompt_json, dict) and 'messages' in prompt_json:
                http_messages = prompt_json['messages']
                prompt = '[JSON structured prompt]'  # for logging
            elif isinstance(prompt_json, list):
                http_messages = prompt_json
                prompt = '[JSON structured prompt]'
            elif isinstance(prompt_json, dict):
                http_messages = [prompt_json] if 'role' in prompt_json else None
                if http_messages:
                    prompt = '[JSON structured prompt]'

        try:
            # Video type handling (HTTP video synthesis endpoints)
            if entry.get('type') == 'video':
                if not endpoint:
                    print(f"No endpoint for {name}, skipping video")
                else:
                    # build payload: prefer explicit input/messages if provided
                    payload = {'model': model, 'input': {}, 'parameters': {}}
                    if entry.get('messages'):
                        payload['input']['messages'] = entry.get('messages')
                    else:
                        payload['input']['prompt'] = prompt
                    # include optional media urls
                    if entry.get('img_url'):
                        payload['input']['img_url'] = entry.get('img_url')
                    if entry.get('audio_url'):
                        payload['input']['audio_url'] = entry.get('audio_url')
                    # merge parameters
                    if entry.get('parameters'):
                        payload['parameters'] = entry.get('parameters')
                    else:
                        payload['parameters'] = {
                            'prompt_extend': entry.get('prompt_extend', True),
                            'resolution': entry.get('resolution', '720P'),
                            'duration': entry.get('duration', 5),
                            'shot_type': entry.get('shot_type', 'single')
                        }

                    # determine POST endpoint by region if not explicitly provided
                    if not endpoint:
                        region = entry.get('region', 'cn')
                        host_map = {
                            'cn': 'https://dashscope.aliyuncs.com',
                            'sg': 'https://dashscope-intl.aliyuncs.com',
                            'us': 'https://dashscope-us.aliyuncs.com'
                        }
                        host = host_map.get(region, host_map['cn'])
                        endpoint = host + '/api/v1/services/aigc/video-generation/video-synthesis'

                    status, data = call_http_video(endpoint, api_key, payload, async_enable=True, timeout=180)
                    video_urls = []
                    if status == 200 and isinstance(data, dict):
                        # try to extract video urls directly
                        output = data.get('output', {})
                        results_out = output.get('results', []) or output.get('choices', []) or []
                        for item in results_out:
                            if isinstance(item, dict) and 'video' in item:
                                video_urls.append(item['video'])
                            elif isinstance(item, dict) and 'url' in item:
                                video_urls.append(item['url'])
                            elif isinstance(item, dict) and 'message' in item:
                                content = item['message'].get('content', [])
                                for it in content:
                                    if isinstance(it, dict) and ('video' in it or 'url' in it):
                                        video_urls.append(it.get('video') or it.get('url'))
                    # if not immediate result, check for request_id and poll
                    if not video_urls:
                        request_id = None
                        if isinstance(data, dict):
                            request_id = data.get('request_id') or data.get('requestId') or data.get('task_id')
                        if request_id:
                            print(f"Video request submitted, request_id={request_id}, polling for result...")
                            st, resp = poll_video_result(endpoint, api_key, request_id, poll_interval=3, max_wait=300)
                            if st == 200 and isinstance(resp, dict) and resp.get('video_urls'):
                                video_urls = resp.get('video_urls')
                            else:
                                print(f"Polling result: {resp}")
                        else:
                            print(f"No video URL and no request_id returned for {name}: {data}")

                    # download any found video urls
                    for i, vurl in enumerate(video_urls, 1):
                        path = download_and_save(vurl, dest_dir, f"{name}_{i}")
                        if path:
                            image_urls.append(vurl)
                            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                                f.write(json.dumps({'time': datetime.now().isoformat(), 'source': name, 'url': vurl, 'file': path}, ensure_ascii=False) + '\n')
                # finished video handling for this entry, continue to next
                results.append({'name': name, 'expires': entry['expires'], 'downloaded': [], 'urls': image_urls})
                time.sleep(1)
                continue
            if method == 'sdk' and model:
                # if entry provides full `messages` structure, pass it to multimodal call
                messages = entry.get('messages')
                n = entry.get('n', 1)
                watermark = entry.get('watermark', False)
                negative_prompt = entry.get('negative_prompt')
                prompt_extend = entry.get('prompt_extend', False)
                resp = call_sdk_image(model, prompt, size, api_key, messages=messages, n=n, watermark=watermark, negative_prompt=negative_prompt, prompt_extend=prompt_extend)
                status_code = getattr(resp, 'status_code', None)
                # handle SDK object-like response or dict
                if status_code is None and isinstance(resp, dict):
                    status_code = resp.get('status_code', 200)
                
                print(f"Debug: {name} status_code={status_code}, resp type={type(resp)}")

                if status_code == HTTPStatus.OK or status_code == 200:
                    # try to extract output.results or output.choices from object or dict
                    output = None
                    if isinstance(resp, dict):
                        output = resp.get('output', {})
                    else:
                        output = getattr(resp, 'output', None)

                    results_out = []
                    if isinstance(output, dict):
                        results_out = output.get('results', []) or output.get('choices', []) or []
                    elif output is not None and hasattr(output, 'results'):
                        results_out = getattr(output, 'results') or []
                    elif output is not None and hasattr(output, 'choices'):
                        results_out = getattr(output, 'choices') or []

                    for item in results_out:
                        try:
                            if isinstance(item, dict):
                                # Check for url in dict (generation model)
                                if 'url' in item:
                                    image_urls.append(item['url'])
                                # Check for nested message.content structure (editing model)
                                elif 'message' in item and isinstance(item['message'], dict):
                                    content = item['message'].get('content', [])
                                    for content_item in content:
                                        if isinstance(content_item, dict):
                                            # image editing returns "image" field instead of "url"
                                            if 'image' in content_item:
                                                image_urls.append(content_item['image'])
                                            elif 'url' in content_item:
                                                image_urls.append(content_item['url'])
                            else:
                                # Handle object with message attribute
                                if hasattr(item, 'message'):
                                    msg = getattr(item, 'message')
                                    if hasattr(msg, 'content'):
                                        content = getattr(msg, 'content')
                                        if isinstance(content, list):
                                            for content_item in content:
                                                if isinstance(content_item, dict):
                                                    if 'image' in content_item:
                                                        image_urls.append(content_item['image'])
                                                    elif 'url' in content_item:
                                                        image_urls.append(content_item['url'])
                        except (KeyError, AttributeError):
                            pass
            else:
                if not endpoint:
                    print(f"No endpoint for {name}, skipping")
                    continue
                # Use http_messages if available (from JSON), else construct from prompt
                status, data = call_http(endpoint, api_key, prompt, size, model, messages=http_messages)
                if status == 200 and isinstance(data, dict):
                    output = data.get('output', {})
                    results_out = output.get('results', []) or output.get('choices', []) or []
                    # normalize: support 'url' and 'image' fields and nested message/content structures
                    for item in results_out:
                        try:
                            if isinstance(item, dict):
                                # direct url or image
                                if 'url' in item:
                                    image_urls.append(item['url'])
                                elif 'image' in item:
                                    image_urls.append(item['image'])
                                # nested message structure
                                elif 'message' in item and isinstance(item['message'], dict):
                                    content = item['message'].get('content', [])
                                    for it in content:
                                        if isinstance(it, dict):
                                            if 'image' in it:
                                                image_urls.append(it['image'])
                                            elif 'url' in it:
                                                image_urls.append(it['url'])
                                            # some responses nest content further
                                            elif 'content' in it and isinstance(it['content'], list):
                                                for ci in it['content']:
                                                    if isinstance(ci, dict):
                                                        if 'image' in ci:
                                                            image_urls.append(ci['image'])
                                                        elif 'url' in ci:
                                                            image_urls.append(ci['url'])
                            else:
                                # handle object-like items with message attribute
                                if hasattr(item, 'message'):
                                    msg = getattr(item, 'message')
                                    if hasattr(msg, 'content'):
                                        content = getattr(msg, 'content')
                                        if isinstance(content, list):
                                            for content_item in content:
                                                if isinstance(content_item, dict):
                                                    if 'image' in content_item:
                                                        image_urls.append(content_item['image'])
                                                    elif 'url' in content_item:
                                                        image_urls.append(content_item['url'])
                        except (KeyError, AttributeError):
                            pass
                else:
                    print(f"Request failed for {name}: status {status} data: {data}")

        except Exception as e:
            print(f"Exception calling {name}: {e}")
            import traceback
            traceback.print_exc()

        saved = []
        for i, url in enumerate(image_urls, 1):
            path = download_and_save(url, dest_dir, f"{name}_{i}")
            if path:
                saved.append(path)
                with open(LOG_FILE, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({
                        'time': datetime.now().isoformat(),
                        'source': name,
                        'url': url,
                        'file': path
                    }, ensure_ascii=False) + '\n')
        results.append({'name': name, 'expires': entry['expires'], 'downloaded': saved, 'urls': image_urls})
        # if downloaded something, decrement quota and persist
        if saved:
            # decrement remaining by 1
            orig = entry.get('remaining','')
            cur = parse_remaining_str(orig)
            new = max(0, cur-1)
            entry['remaining'] = format_remaining_str(new, orig)
            # persist back to input file if provided
            if input_file:
                try:
                    # reload full list to avoid overwriting concurrent changes
                    with open(input_file, 'r', encoding='utf-8') as f:
                        full = json.load(f)
                    # find and update matching entry by name first, then fall back to model
                    found_match = False
                    for fe in full:
                        if fe.get('name') == entry.get('name'):
                            fe['remaining'] = entry['remaining']
                            found_match = True
                            break
                    # if no name match, try matching by model (fallback for unnamed entries)
                    if not found_match:
                        for fe in full:
                            if fe.get('model') == entry.get('model') and fe.get('name') == entry.get('name'):
                                fe['remaining'] = entry['remaining']
                                break
                    with open(input_file, 'w', encoding='utf-8') as f:
                        json.dump(full, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"Warning: failed to persist quota update: {e}")
        # small pause to avoid rate limits
        time.sleep(1)

    return results


def main():
    p = argparse.ArgumentParser(description='Auto-generate images from expiring model endpoints and download results.')
    p.add_argument('--input', '-i', default='models_to_use.json', help='JSON file with model entries')
    p.add_argument('--api-key', '-k', default=None, help='API key (overrides env DASHSCOPE_API_KEY)')
    p.add_argument('--out', '-o', default=DEFAULT_OUTPUT_DIR, help='Output directory for downloaded images')
    p.add_argument('--prompt', help='Override prompt for all entries')
    p.add_argument('--prompt-json', help='JSON file containing structured prompt (messages array or full payload)')
    p.add_argument('--yes', '-y', action='store_true', help='Bypass prompt confirmation and run without interactive prompt')
    p.add_argument('--model', '-m', help='Only run the specified model name (matches entry name or model)')
    p.add_argument('--size', help='Override size for all entries (e.g. 1024*1024)')
    p.add_argument('--single', action='store_true', help='Only use the next-expiring model (generate one image)')
    p.add_argument('--add-quota', nargs=2, metavar=('MODEL','COUNT'), help='Add COUNT quota to model (name or model) and exit')
    p.add_argument('--type', '-t', default='generation', choices=['generation', 'edit', 'all'], help='Model type: generation, edit, or all')
    args = p.parse_args()
    # Safety: require explicit prompt, prompt-json, or --yes to run to avoid accidental bulk generation
    if not args.prompt and not args.prompt_json and not args.yes:
        print('安全开关：未提供 --prompt、--prompt-json 或未使用 --yes，脚本将退出以避免误触发生成。')
        print('如需继续，请使用 `--prompt "你的提示词"` 或 `--prompt-json <文件>` 或添加 `--yes` 强制运行。')
        sys.exit(0)

    api_key = args.api_key or os.environ.get('DASHSCOPE_API_KEY') or os.environ.get('API_KEY')
    if not api_key:
        print('API key required via --api-key or env DASHSCOPE_API_KEY')
        sys.exit(1)

    # Load structured prompt from JSON if provided
    prompt_json_data = None
    if args.prompt_json:
        if not os.path.exists(args.prompt_json):
            print(f"Error: Prompt JSON file '{args.prompt_json}' not found")
            sys.exit(1)
        try:
            with open(args.prompt_json, 'r', encoding='utf-8') as f:
                prompt_json_data = json.load(f)
        except Exception as e:
            print(f"Error loading prompt JSON: {e}")
            sys.exit(1)

    if not os.path.exists(args.input):
        sample = [
            {"name": "z-image-turbo-1", "url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation", "model": "z-image-turbo", "expires": "2026-02-06", "size": "1120*1440", "type": "generation"}
        ]
        with open(args.input, 'w', encoding='utf-8') as f:
            json.dump(sample, f, ensure_ascii=False, indent=2)
        print(f"Sample input written to {args.input}. Please edit with your URLs and expiry dates.")
        print("Format: [{name,url,model,expires,size,method,type}] where method is 'http' or 'sdk', type is 'generation' or 'edit'.")
        sys.exit(0)

    with open(args.input, 'r', encoding='utf-8') as f:
        entries = json.load(f)

    # If --model specified, filter entries to only that model (match name or model)
    if args.model:
        m = args.model
        entries = [e for e in entries if (e.get('name') == m or e.get('model') == m)]
        if not entries:
            print(f"No entries matching model '{m}' found in {args.input}")
            sys.exit(1)

    # handle add-quota operation (no prompt needed)
    if args.add_quota:
        target, cnt = args.add_quota
        try:
            cnt = int(cnt)
        except Exception:
            print('COUNT must be integer')
            sys.exit(1)
        found = False
        for e in entries:
            if e.get('name') == target or e.get('model') == target:
                orig = e.get('remaining','')
                cur = parse_remaining_str(orig)
                new = cur + cnt
                e['remaining'] = format_remaining_str(new, orig)
                found = True
                break
        if not found:
            print(f"Model '{target}' not found in {args.input}")
            sys.exit(1)
        # write back
        with open(args.input, 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        print(f"Added {cnt} quota to {target}. New remaining: {e['remaining']}")
        sys.exit(0)

    model_type = args.type if args.type != 'all' else None
    max_entries = 1 if args.single else None
    results = process_entries(entries, api_key, args.out, default_prompt=args.prompt, default_size=args.size or '1024*1024', model_type=model_type, max_entries=max_entries, input_file=args.input, prompt_json=prompt_json_data)
    print('Done. Summary:')
    for r in results:
        print(f"- {r['name']}: downloaded {len(r['downloaded'])} files")


if __name__ == '__main__':
    main()
