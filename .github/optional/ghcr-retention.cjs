// Inspect every tagged manifest before delet
ing untagged platform/attestation candidates.

const {execFileSync} = require('node:child_p
rocess');
const manifestTypes = new Set([
  '
application/vnd.oci.image.manifest.v1+json',

  'application/vnd.docker.distribution.manife
st.v2+json',
]);
const configTypes = new Set(
[
  'application/vnd.oci.image.config.v1+json
',
  'application/vnd.docker.container.image.
v1+json',
]);
const layerTypes = new Set([
  
'application/vnd.oci.image.layer.v1.tar',
  '
application/vnd.oci.image.layer.v1.tar+gzip',

  'application/vnd.oci.image.layer.v1.tar+zs
td',
  'application/vnd.oci.image.layer.nondi
stributable.v1.tar',
  'application/vnd.oci.i
mage.layer.nondistributable.v1.tar+gzip',
  '
application/vnd.oci.image.layer.nondistributa
ble.v1.tar+zstd',
  'application/vnd.docker.i
mage.rootfs.diff.tar.gzip',
  'application/vn
d.docker.image.rootfs.foreign.diff.tar.gzip',

]);
function descriptorIsKnown(descriptor, t
ypes) {
  return descriptor && types.has(desc
riptor.mediaType) &&
    /^sha256:[a-f0-9]{64
}$/.test(descriptor.digest) &&
    Number.isS
afeInteger(descriptor.size) && descriptor.siz
e >= 0;
}
function isRunnableManifest(manifes
t) {
  return manifest && manifest.schemaVers
ion === 2 &&
    manifestTypes.has(manifest.m
ediaType) &&
    !Object.hasOwn(manifest, 'ma
nifests') &&
    !Object.hasOwn(manifest, 'su
bject') &&
    !Object.hasOwn(manifest, 'arti
factType') &&
    descriptorIsKnown(manifest.
config, configTypes) &&
    Array.isArray(man
ifest.layers) &&
    manifest.layers.every(la
yer => descriptorIsKnown(layer, layerTypes));

}
module.exports = async ({github, context, 
core}) => {
  const owner = context.repo.owne
r;
  const pkg = process.env.PACKAGE_NAME;
  
const {data: account} = await github.rest.use
rs.getByUsername({username: owner});
  const 
prefix = account.type === 'Organization' ? 'o
rgs' : 'users';
  const route = 'GET /' + pre
fix + '/' + encodeURIComponent(owner) +
    '
/packages/container/' + encodeURIComponent(pk
g) + '/versions';
  const versions = await gi
thub.paginate(route, {per_page: 100});
  cons
t tagged = versions.filter(v => v.metadata?.c
ontainer?.tags?.length)
    .sort((a, b) => D
ate.parse(b.created_at) - Date.parse(a.create
d_at));
  for (const version of tagged) {
   
 if (!/^sha256:[a-f0-9]{64}$/.test(version.na
me)) {
      throw new Error('Unexpected pack
age digest; cleanup stopped.');
    }
    con
st ref = 'ghcr.io/' + owner.toLowerCase() + '
/' + pkg + '@' + version.name;
    const mani
fest = JSON.parse(execFileSync('docker',
    
  ['buildx', 'imagetools', 'inspect', '--raw'
, ref],
      {encoding: 'utf8', timeout: 600
00, maxBuffer: 8 * 1024 * 1024}));
    // Leg
acy attestations have ordinary config/layers 
fields but in-toto layers.
    // Only known 
runnable image media types permit any destruc
tive cleanup.
    if (!isRunnableManifest(man
ifest)) {
      throw new Error('An index, at
testation, or unknown manifest exists; cleanu
p stopped.');
    }
  }
  const keep = new Se
t(tagged.slice(0, 3).map(v => v.id));
  for (
const v of tagged) {
    if (v.metadata.conta
iner.tags.includes('latest')) keep.add(v.id);

  }
  // At most 100 deletions per run; subs
equent runs drain any backlog.
  const expire
d = tagged.filter(v => !keep.has(v.id)).rever
se().slice(0, 100);
  core.setOutput('tagged_
ids', expired.map(v => v.id).join(','));
  co
re.setOutput('safe_single_arch', 'true');
  c
ore.info('Manifest guard passed. Retaining at
 least three tagged versions and latest.');
}
;


