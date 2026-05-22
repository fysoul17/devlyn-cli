import { User } from './models';

export function getUserById(req, res) {
  const user = User.findOne({ where: { id: req.params.id } });
  res.json(user);
}
