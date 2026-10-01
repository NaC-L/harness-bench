// Small test-side tokenizer for this server-rendered form; not a browser emulator.
export function decode(text) {
  return text.replace(/&(#x[0-9a-f]+|#\d+|amp|lt|gt|quot|apos);/gi, (_, entity) => {
    if (entity[0] === '#') return String.fromCodePoint(entity[1].toLowerCase() === 'x' ? parseInt(entity.slice(2), 16) : Number(entity.slice(1)));
    return {amp: '&', lt: '<', gt: '>', quot: '"', apos: "'"}[entity.toLowerCase()];
  });
}
export function parse(html) {
  const root = {tag: '#root', attrs: {}, children: []};
  const stack = [root];
  const tokens = html.match(/<!--[\s\S]*?-->|<\/?[a-z][^>]*>|[^<]+/gi) || [];
  for (const token of tokens) {
    if (token.startsWith('<!--')) continue;
    if (token.startsWith('</')) {
      const tag = token.match(/^<\/([\w-]+)/)[1].toLowerCase();
      const index = stack.findLastIndex(node => node.tag === tag);
      if (index > 0) stack.length = index;
    } else if (token.startsWith('<')) {
      const [, tag, rest] = token.match(/^<([\w-]+)([\s\S]*)>$/);
      const attrs = {};
      for (const match of rest.matchAll(/([^\s=/'">]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g)) attrs[match[1].toLowerCase()] = decode(match[2] ?? match[3] ?? match[4] ?? '');
      const node = {tag: tag.toLowerCase(), attrs, children: [], parent: stack.at(-1)};
      stack.at(-1).children.push(node);
      if (!['input', 'br', 'hr', 'img', 'meta', 'link'].includes(node.tag) && !token.endsWith('/>')) stack.push(node);
    } else stack.at(-1).children.push(decode(token));
  }
  return root;
}
export function nodes(root, predicate) {
  return root.children.flatMap(child => typeof child === 'string' ? [] : [...(predicate(child) ? [child] : []), ...nodes(child, predicate)]);
}
export function text(node) { return node.children.map(child => typeof child === 'string' ? child : text(child)).join(''); }
export function control(root, name) { return nodes(root, node => node.tag === 'input' && node.attrs.name === name)[0]; }
export function byId(root, id) { return nodes(root, node => node.attrs.id === id)[0]; }
