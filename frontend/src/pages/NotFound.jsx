import { Link } from 'react-router-dom'
import { PageHeader } from '../components/ui'

export default function NotFound() {
  return (
    <div className="py-12">
      <PageHeader eyebrow="404" title="Page not found" description="The page you requested does not exist. It may have been moved, or the link may be mistyped." />
      <Link to="/" className="btn-primary">
        Go to the dashboard
      </Link>
    </div>
  )
}
