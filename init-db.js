db.createUser({
  user: 'mcd_user',
  pwd: 'mcd',
  roles: [
    {
      role: 'readWrite',
      db: 'mcd',
    },
  ],
});

db = db.getSiblingDB('mcd');
