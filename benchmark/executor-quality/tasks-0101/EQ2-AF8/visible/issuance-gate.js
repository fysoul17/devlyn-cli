export class IssuanceGate {
  continue(authorization, assessment, issue) {
    if (!authorization.ok) {
      return authorization;
    }
    if (!assessment.ok) {
      return assessment;
    }
    return issue();
  }
}
