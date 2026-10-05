'use strict';

/**
 * Ghost 5 official-theme install downloads GitHub zipballs.
 * Those archives often have Unix mode 000 and include .github/,
 * so gscan/extract-zip fails with EACCES inside Docker.
 * This preload rewrites every .zip Ghost writes before extract.
 */

const Module = require('module');
const zlib = require('zlib');

function u16(buf, off) {
    return buf.readUInt16LE(off);
}

function u32(buf, off) {
    return buf.readUInt32LE(off);
}

function shouldDrop(name) {
    const n = name.replace(/\\/g, '/');
    return n.includes('.github/') || n === '.github' || n.endsWith('/.github') || n.endsWith('/.github/');
}

const GHOST5_SOCIAL = [
    '{{#if @site.facebook}}',
    '<a href="{{facebook_url @site.facebook}}" target="_blank" rel="noopener" aria-label="Facebook">{{> "icons/facebook"}}</a>',
    '{{/if}}',
    '{{#if @site.twitter}}',
    '<a href="{{twitter_url}}" target="_blank" rel="noopener" aria-label="X">{{> "icons/x"}}</a>',
    '{{/if}}'
].join('');

function rewriteForGhost5(name, raw) {
    if (!name.toLowerCase().endsWith('.hbs') || !raw || !raw.length) {
        return raw;
    }
    let text = raw.toString('utf8');
    if (!text.includes('social_accounts')) {
        return raw;
    }
    text = text.replace(/\{\{#social_accounts[\s\S]*?\{\{\/social_accounts\}\}/g, GHOST5_SOCIAL);
    return Buffer.from(text, 'utf8');
}

function sanitizeZip(input) {
    const buf = Buffer.isBuffer(input) ? input : Buffer.from(input);
    let eocd = -1;
    for (let i = buf.length - 22; i >= 0 && i >= buf.length - 22 - 0xffff; i--) {
        if (buf.readUInt32LE(i) === 0x06054b50) {
            eocd = i;
            break;
        }
    }
    if (eocd < 0) {
        throw new Error('EOCD not found');
    }
    const count = u16(buf, eocd + 10);
    const cdSize = u32(buf, eocd + 12);
    const cdOff = u32(buf, eocd + 16);
    const locals = [];
    let cdPos = cdOff;
    for (let i = 0; i < count; i++) {
        if (u32(buf, cdPos) !== 0x02014b50) {
            throw new Error('bad central directory');
        }
        const method = u16(buf, cdPos + 10);
        const nameLen = u16(buf, cdPos + 28);
        const extraLen = u16(buf, cdPos + 30);
        const commentLen = u16(buf, cdPos + 32);
        const extAttr = u32(buf, cdPos + 38);
        const localOff = u32(buf, cdPos + 42);
        const name = buf.slice(cdPos + 46, cdPos + 46 + nameLen).toString('utf8');
        cdPos += 46 + nameLen + extraLen + commentLen;
        if (shouldDrop(name)) {
            continue;
        }
        if (u32(buf, localOff) !== 0x04034b50) {
            throw new Error('bad local header');
        }
        const lNameLen = u16(buf, localOff + 26);
        const lExtraLen = u16(buf, localOff + 28);
        const compSize = u32(buf, localOff + 18);
        const dataStart = localOff + 30 + lNameLen + lExtraLen;
        const compressed = buf.slice(dataStart, dataStart + compSize);
        let raw;
        if (name.endsWith('/') || (extAttr & 0x10)) {
            raw = Buffer.alloc(0);
        } else if (method === 0) {
            raw = compressed;
        } else if (method === 8) {
            raw = zlib.inflateRawSync(compressed);
        } else {
            throw new Error('unsupported method ' + method);
        }
        locals.push({
            name,
            raw: rewriteForGhost5(name, raw),
            date: buf.slice(localOff + 10, localOff + 14)
        });
    }

    const out = [];
    const central = [];
    let offset = 0;
    for (const entry of locals) {
        const nameBuf = Buffer.from(entry.name, 'utf8');
        const isDir = entry.name.endsWith('/');
        const raw = isDir ? Buffer.alloc(0) : entry.raw;
        const compressed = isDir ? Buffer.alloc(0) : zlib.deflateRawSync(raw);
        const crc = crc32(raw);
        const local = Buffer.alloc(30);
        local.writeUInt32LE(0x04034b50, 0);
        local.writeUInt16LE(20, 4);
        local.writeUInt16LE(0, 6);
        local.writeUInt16LE(8, 8);
        entry.date.copy(local, 10);
        local.writeUInt32LE(crc, 14);
        local.writeUInt32LE(compressed.length, 18);
        local.writeUInt32LE(raw.length, 22);
        local.writeUInt16LE(nameBuf.length, 26);
        local.writeUInt16LE(0, 28);
        const localOff = offset;
        out.push(local, nameBuf, compressed);
        offset += local.length + nameBuf.length + compressed.length;

        const mode = isDir ? 0o40755 : 0o100644;
        const ext = (mode << 16) | (isDir ? 0x10 : 0);
        const cd = Buffer.alloc(46);
        cd.writeUInt32LE(0x02014b50, 0);
        cd.writeUInt16LE(20, 4);
        cd.writeUInt16LE(20, 6);
        cd.writeUInt16LE(0, 8);
        cd.writeUInt16LE(8, 10);
        entry.date.copy(cd, 12);
        cd.writeUInt32LE(crc, 16);
        cd.writeUInt32LE(compressed.length, 20);
        cd.writeUInt32LE(raw.length, 24);
        cd.writeUInt16LE(nameBuf.length, 28);
        cd.writeUInt16LE(0, 30);
        cd.writeUInt16LE(0, 32);
        cd.writeUInt16LE(0, 34);
        cd.writeUInt16LE(0, 36);
        cd.writeUInt32LE(ext >>> 0, 38);
        cd.writeUInt32LE(localOff, 42);
        central.push(cd, nameBuf);
    }

    const cdStart = offset;
    for (const part of central) {
        out.push(part);
        offset += part.length;
    }
    const eocdBuf = Buffer.alloc(22);
    eocdBuf.writeUInt32LE(0x06054b50, 0);
    eocdBuf.writeUInt16LE(0, 4);
    eocdBuf.writeUInt16LE(0, 6);
    eocdBuf.writeUInt16LE(locals.length, 8);
    eocdBuf.writeUInt16LE(locals.length, 10);
    eocdBuf.writeUInt32LE(offset - cdStart, 12);
    eocdBuf.writeUInt32LE(cdStart, 16);
    eocdBuf.writeUInt16LE(0, 20);
    out.push(eocdBuf);
    return Buffer.concat(out);
}

function crc32(buf) {
    let crc = ~0;
    for (let i = 0; i < buf.length; i++) {
        crc = (crc >>> 8) ^ CRC_TABLE[(crc ^ buf[i]) & 0xff];
    }
    return (~crc) >>> 0;
}

const CRC_TABLE = new Uint32Array(256);
for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) {
        c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
    }
    CRC_TABLE[n] = c >>> 0;
}

function maybeSanitize(p, data) {
    if (!p || !String(p).toLowerCase().endsWith('.zip')) {
        return data;
    }
    if (!Buffer.isBuffer(data) && !(data instanceof Uint8Array)) {
        return data;
    }
    try {
        const buf = Buffer.isBuffer(data) ? data : Buffer.from(data);
        if (buf.length < 4 || buf[0] !== 0x50 || buf[1] !== 0x4b) {
            return data;
        }
        const cleaned = sanitizeZip(buf);
        if (cleaned && cleaned.length > 22) {
            process.stdout.write('[tuhoy] sanitized theme zip ' + String(p) + '\n');
            return cleaned;
        }
    } catch (err) {
        process.stderr.write('[tuhoy] zip sanitize failed: ' + (err && err.message) + '\n');
    }
    return data;
}

function patchFsExtra(exp) {
    if (!exp || exp.__tuhoyPatched) {
        return exp;
    }
    const orig = exp.writeFile.bind(exp);
    exp.writeFile = function (p, data, opts) {
        return orig(p, maybeSanitize(p, data), opts);
    };
    exp.__tuhoyPatched = true;
    return exp;
}

function patchRequest(exp) {
    if (!exp || exp.__tuhoyPatched) {
        return exp;
    }
    const orig = typeof exp === 'function' ? exp : null;
    if (!orig) {
        return exp;
    }
    const wrapped = function (url, options) {
        const opts = Object.assign({}, options || {});
        opts.headers = Object.assign({
            'user-agent': 'Ghost/5.130 (TuHoy official-theme-install)'
        }, opts.headers || {});
        return orig(url, opts);
    };
    Object.assign(wrapped, exp);
    wrapped.__tuhoyPatched = true;
    return wrapped;
}

const origLoad = Module._load;
Module._load = function (request, parent, isMain) {
    const exp = origLoad.apply(this, arguments);
    if (request === 'fs-extra') {
        return patchFsExtra(exp);
    }
    if (request === '@tryghost/request') {
        return patchRequest(exp);
    }
    return exp;
};

process.stdout.write('[tuhoy] official theme zip sanitizer loaded\n');

module.exports = {sanitizeZip, maybeSanitize};
