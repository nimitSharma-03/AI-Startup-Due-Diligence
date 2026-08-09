import { Activity } from 'lucide-react'
import { NavLink } from 'react-router-dom'

function Navbar() { return <header className="nav"><NavLink className="brand" to="/"><span className="brand-mark"><Activity size={18} /></span>VentureSignal</NavLink><nav className="nav-links"><NavLink className="nav-link" to="/">Dashboard</NavLink><NavLink className="nav-link" to="/about">About</NavLink></nav></header> }
export default Navbar
