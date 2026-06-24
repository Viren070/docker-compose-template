const userToCreate = fs.readFileSync('/run/secrets/jikan_db_username', 'utf8').trim();
const userPassword = fs.readFileSync('/run/secrets/jikan_db_password', 'utf8').trim();
db = db.getSiblingDB("admin");
db.createUser({ user: userToCreate, pwd: userPassword, roles: [{ role: "readWrite", db: "jikan" }] });
db = db.getSiblingDB("jikan");
db.createUser({ user: userToCreate, pwd: userPassword, roles: [{ role: "readWrite", db: "jikan" }] });