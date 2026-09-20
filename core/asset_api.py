"""Persistent A14 sources. Deletes archive records, never unlink run evidence."""
import hashlib
import io
import json
from pathlib import Path
from uuid import uuid4
import pandas as pd
from django.conf import settings
from django.http import JsonResponse, FileResponse
from django.views.decorators.http import require_http_methods
from .models import FileAsset


def owner(request):
    return request.user.pk if request.user.is_authenticated else None


def visible_assets(request):
    return FileAsset.objects.filter(project='A14', owner_id=owner(request))


def public(asset):
    return {'asset_id': asset.asset_id, 'project': asset.project, 'display_name': asset.display_name,
            'source_type': asset.source_type, 'content_hash': asset.content_hash, 'size': asset.size,
            'rows': asset.rows, 'columns': asset.columns, 'created_at': asset.created_at.isoformat(),
            'status': asset.status, 'related_runs': asset.related_runs}


def register_asset(path, name, request, source_type='upload'):
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if source_type == 'simulation' or Path(name).name.startswith('SYNTHETIC_'):
        source_type = 'SYNTHETIC'
    asset_id = 'asset_' + uuid4().hex
    root = Path(settings.PROCESSPILOT_RUNTIME_ROOT) / 'file_assets'
    root.mkdir(parents=True, exist_ok=True)
    storage = root / (asset_id + '.csv')
    rows = columns = None
    try:
        frame = pd.read_csv(io.BytesIO(raw))
        rows, columns = frame.shape
    except (ValueError, UnicodeError, pd.errors.ParserError):
        pass
    storage.write_bytes(raw)
    try:
        return FileAsset.objects.create(asset_id=asset_id, owner_id=owner(request), display_name=Path(name).name[:255],
            storage_ref=storage.name, source_type=source_type, content_hash=digest, size=len(raw), rows=rows, columns=columns)
    except Exception:
        storage.unlink(missing_ok=True)
        raise


@require_http_methods(['GET', 'POST'])
def assets(request):
    if request.method == 'GET':
        return JsonResponse({'ok': True, 'data': [public(a) for a in visible_assets(request).filter(status='active')[:500]]})
    upload = request.FILES.get('file')
    if not upload or not upload.name.lower().endswith('.csv') or upload.size > 200 * 1024 * 1024:
        return JsonResponse({'ok': False, 'message': '请选择不超过 200 MB 的 CSV。'}, status=400)
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'source.csv'
        with path.open('wb') as out:
            for chunk in upload.chunks(): out.write(chunk)
        sidecars = {}
        try:
            for key in ('generation_manifest', 'evaluation_reference'):
                raw = request.POST.get(key)
                if raw is not None:
                    if len(raw.encode('utf-8')) > 4 * 1024 * 1024:
                        raise ValueError('生成附录超过 4 MB')
                    value = json.loads(raw)
                    if not isinstance(value, dict):
                        raise ValueError('生成附录必须为 JSON 对象')
                    sidecars[key] = value
            if sidecars:
                manifest = sidecars.get('generation_manifest', {})
                if manifest.get('source_type') != 'SYNTHETIC' or manifest.get('file_hash') != hashlib.sha256(path.read_bytes()).hexdigest():
                    raise ValueError('合成数据清单与 CSV 哈希不一致')
                required = {'preset_id', 'preset_version', 'scenario_id', 'generator_version', 'explicit_seed', 'effective_generation_parameters', 'rows', 'sampling_interval', 'units', 'process_assumptions'}
                if not required.issubset(manifest):
                    raise ValueError('合成数据清单缺少必要字段')
        except (ValueError, TypeError) as exc:
            return JsonResponse({'ok': False, 'message': str(exc)}, status=400)
        synthetic = sidecars or request.POST.get('source_type') in ('simulation', 'SYNTHETIC')
        asset = register_asset(path, upload.name, request, 'SYNTHETIC' if synthetic else 'upload')
        # These are independent audit downloads, never run artifacts, features,
        # retrieval documents or LLM context. The manifest grants no exemption.
        for key, value in sidecars.items():
            target = Path(settings.PROCESSPILOT_RUNTIME_ROOT) / 'file_assets' / f'{asset.asset_id}.{key}.json'
            target.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return JsonResponse({'ok': True, 'data': public(asset)}, status=201)


@require_http_methods(['GET', 'DELETE'])
def asset_detail(request, asset_id):
    asset = visible_assets(request).filter(asset_id=asset_id).first()
    if not asset:
        return JsonResponse({'ok': False, 'message': '资产不存在或无访问权限。'}, status=404)
    if request.method == 'DELETE':
        asset.status = 'archived'
        asset.save(update_fields=['status'])
        return JsonResponse({'ok': True, 'data': public(asset), 'message': '已归档；运行复现副本保留。'})
    if request.GET.get('artifact') in ('generation_manifest', 'evaluation_reference'):
        key = request.GET['artifact']
        path = Path(settings.PROCESSPILOT_RUNTIME_ROOT) / 'file_assets' / f'{asset.asset_id}.{key}.json'
        if asset.status != 'active' or not path.is_file():
            return JsonResponse({'ok': False, 'message': '生成附录不可用。'}, status=404)
        return FileResponse(path.open('rb'), as_attachment=True, filename=f'SYNTHETIC_{asset.asset_id}_{key}.json')
    if request.GET.get('download') == '1' or request.GET.get('preview') == '1':
        if asset.status != 'active':
            return JsonResponse({'ok': False, 'message': '资产已归档。'}, status=410)
        root = (Path(settings.PROCESSPILOT_RUNTIME_ROOT) / 'file_assets').resolve()
        path = (root / asset.storage_ref).resolve()
        if root not in path.parents or not path.is_file():
            return JsonResponse({'ok': False, 'message': '资产文件不可用。'}, status=404)
        if request.GET.get('preview') == '1':
            from .services.pipeline import _json_safe
            try: preview = _json_safe(pd.read_csv(path, nrows=12).to_dict('records'))
            except (ValueError, UnicodeError, pd.errors.ParserError): preview = []
            return JsonResponse({'ok': True, 'data': {**public(asset), 'preview': preview}}, json_dumps_params={'allow_nan': False})
        return FileResponse(path.open('rb'), as_attachment=True, filename=asset.display_name)
    return JsonResponse({'ok': True, 'data': public(asset)})
