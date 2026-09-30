import pathlib
import sys
import time

mode = sys.argv[1]
if mode == 'hang':
    time.sleep(60)
elif mode in ('solve', 'tamper'):
    pathlib.Path('src/value.js').write_text('module.exports = 42;\n', encoding='utf-8')
    if mode == 'tamper':
        pathlib.Path('test/visible.test.js').write_text('// tampered\n', encoding='utf-8')
        pathlib.Path('test/extra.test.js').write_text('throw new Error("extra")\n', encoding='utf-8')
elif mode == 'regress':
    pathlib.Path('src/value.js').write_text('module.exports = 42;\n', encoding='utf-8')
    pathlib.Path('src/helper.js').write_text('module.exports = 0;\n', encoding='utf-8')
elif mode == 'error':
    sys.exit(3)
print('fake harness done')
